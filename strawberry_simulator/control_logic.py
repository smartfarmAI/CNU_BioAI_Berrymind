import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple

# 비즈니스 룰 로드
def load_business_rules():
    try:
        with open('business_rules.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("business_rules.json 파일을 찾을 수 없습니다.")
        return {}

RULES = load_business_rules()

def validate_sensor(value, sensor_name):
    """센서값 유효성 검증"""
    limits = RULES.get('SENSOR_LIMITS', {}).get(sensor_name)
    if not limits:
        return True
    
    if limits.get('binary'):
        return isinstance(value, bool)
    
    if 'min' in limits and value < limits['min']:
        return False
    if 'max' in limits and value > limits['max']:
        return False
    
    return True

def determine_section(now, sunrise, sunset):
    """현재 시간에 따른 구간 결정"""
    def to_hour(time_str):
        h, m = map(int, time_str.split(':'))
        return h + m/60
    
    sunrise_hour = to_hour(sunrise)
    sunset_hour = to_hour(sunset)
    current_hour = now.hour + now.minute/60
    
    if current_hour < sunrise_hour - 3:
        return 7
    elif current_hour < sunrise_hour:
        return 8
    elif current_hour < sunrise_hour + 3:
        return 1
    elif current_hour < 12:
        return 2
    elif current_hour < sunset_hour - 3:
        return 3
    elif current_hour < sunset_hour:
        return 4
    elif current_hour < sunset_hour + 3:
        return 5
    elif current_hour < 24:
        return 6
    else:
        return 7

class FOGController:
    """FOG 분무 제어"""
    def __init__(self):
        self.start_time = None
        self.stop_time = None
        self.last_status = None
        
    def update(self, sensors, section, current_time) -> Tuple[Dict, Optional[str]]:
        fog_config = RULES.get('FOG_CONTROL', {}).get(str(section), {})
        threshold = fog_config.get('threshold', 0)
        run_time = fog_config.get('run_time', 0)  # ms
        delay_time = fog_config.get('delay_time', 0)  # ms
        
        logic_name = f"FOG_구간{section}_온도기준"
        log_message = None
        
        if sensors['rain'] or run_time == 0 or sensors['temperature'] < threshold:
            if self.start_time or self.stop_time:
                if sensors['rain']:
                    log_message = f"{logic_name}: 강우감지로 중지"
                elif run_time == 0:
                    log_message = f"{logic_name}: 구간{section} 비활성 시간대로 중지"
                else:
                    log_message = f"{logic_name}: 온도 {sensors['temperature']}℃ < {threshold}℃로 중지"
                    
            self.start_time = self.stop_time = None
            current_status = '중지'
            result = {'status': current_status, 'code': 0}
        else:
            if not self.start_time and not self.stop_time:
                self.start_time = current_time
                current_status = '동작'
                log_message = f"{logic_name}: 온도 {sensors['temperature']}℃ ≥ {threshold}℃로 분무 시작"
                result = {'status': current_status, 'code': 1}
            elif self.start_time:
                elapsed = (current_time - self.start_time).total_seconds() * 1000
                if elapsed < run_time:
                    current_status = '동작'
                    result = {'status': current_status, 'code': 1}
                else:
                    self.stop_time = current_time
                    self.start_time = None
                    current_status = '중지'
                    log_message = f"{logic_name}: {int(run_time/1000)}초 동작 완료, {int(delay_time/60000)}분 대기"
                    result = {'status': current_status, 'code': 0}
            elif self.stop_time:
                elapsed = (current_time - self.stop_time).total_seconds() * 1000
                if elapsed < delay_time:
                    current_status = '중지'
                    result = {'status': current_status, 'code': 0}
                else:
                    self.stop_time = None
                    if sensors['temperature'] >= threshold:
                        self.start_time = current_time
                        current_status = '동작'
                        log_message = f"{logic_name}: 대기완료, 온도 {sensors['temperature']}℃로 재시작"
                        result = {'status': current_status, 'code': 1}
                    else:
                        current_status = '중지'
                        result = {'status': current_status, 'code': 0}
        
        self.last_status = result['status']
        return result, log_message

class FCUController:
    """FCU 팬코일 제어"""
    def __init__(self):
        self.state = {}
        
    def update(self, sensors, section, current_time) -> Tuple[Dict, Optional[str]]:
        fcu_config = RULES.get('FCU_CONTROL', {}).get(str(section))
        logic_name = f"FCU_구간{section}_온도제어"
        log_message = None
        
        if not fcu_config:
            return {'status': '대기', 'code': 2}, None
            
        on_threshold = fcu_config['on_threshold']
        off_threshold = fcu_config['off_threshold']
        
        if section not in self.state:
            self.state[section] = 'off'
            
        if self.state[section] == 'off' and sensors['temperature'] >= on_threshold:
            self.state[section] = 'on'
            log_message = f"{logic_name}: 온도 {sensors['temperature']}℃ ≥ {on_threshold}℃로 냉방 시작"
            return {'status': '동작', 'code': 1}, log_message
        elif self.state[section] == 'on' and sensors['temperature'] <= off_threshold:
            self.state[section] = 'off'
            log_message = f"{logic_name}: 온도 {sensors['temperature']}℃ ≤ {off_threshold}℃로 냉방 중지"
            return {'status': '중지', 'code': 0}, log_message
        else:
            status_text = '동작' if self.state[section] == 'on' else '중지'
            code = 1 if self.state[section] == 'on' else 0
            return {'status': status_text, 'code': code}, None

class CO2Controller:
    """CO2 공급 제어"""
    def __init__(self):
        self.last_status = None
        
    def update(self, sensors, section, current_time) -> Tuple[Dict, Optional[str]]:
        co2_config = RULES.get('CO2_CONTROL', {}).get(str(section), {})
        trigger = co2_config.get('trigger', 200)
        target = co2_config.get('target', 300)
        original_target = target
        
        logic_name = f"CO2_구간{section}_농도제어"
        log_message = None
        
        # 대전제 적용
        modifiers = RULES.get('CO2_MODIFIERS', {})
        modifiers_text = []
        
        if sensors['light'] <= modifiers.get('light_threshold', 50):
            target *= modifiers.get('light_multiplier', 0.8)
            modifiers_text.append(f"일사량{sensors['light']}≤50(×0.8)")
        if sensors['rain']:
            target *= modifiers.get('rain_multiplier', 0.6)
            modifiers_text.append("강우(×0.6)")
        if sensors['humidity'] >= modifiers.get('humidity_threshold', 85):
            target *= modifiers.get('humidity_multiplier', 0.7)
            modifiers_text.append(f"습도{sensors['humidity']}%≥85%(×0.7)")
            
        if sensors['co2'] <= trigger or sensors['co2'] < target:
            current_status = f'{round(target)}ppm 공급중'
            if self.last_status != current_status:
                if modifiers_text:
                    log_message = f"{logic_name}: CO₂ {sensors['co2']}ppm < {round(target)}ppm, 보정조건({', '.join(modifiers_text)})"
                else:
                    log_message = f"{logic_name}: CO₂ {sensors['co2']}ppm < {round(target)}ppm으로 공급 시작"
            result = {'status': current_status, 'code': 1}
        else:
            current_status = '대기'
            if self.last_status and '공급중' in self.last_status:
                log_message = f"{logic_name}: CO₂ {sensors['co2']}ppm ≥ {round(target)}ppm으로 공급 완료"
            result = {'status': current_status, 'code': 2}
            
        self.last_status = current_status
        return result, log_message

class CurtainController:
    """보온커튼 제어"""
    def __init__(self):
        self.start_time = None
        self.last_status = None
        
    def update(self, sensors, section, current_time) -> Tuple[Dict, Optional[str]]:
        curtain_config = RULES.get('CURTAIN_CONTROL', {})
        logic_name = f"보온커튼_구간{section}_온도제어"
        log_message = None
        
        if section == 1:
            config = curtain_config.get('1', {})
            threshold = config.get('base_threshold', 15)
            original_threshold = threshold
            
            # 외기온에 따른 임계값 조정
            if sensors['out_temp'] >= 0:
                threshold = config['out_temp_adjustments']['above_0']
            elif sensors['out_temp'] >= -10:
                threshold = config['out_temp_adjustments']['minus_10_to_0']
                
            if sensors['temperature'] >= threshold:
                if not self.start_time:
                    self.start_time = current_time
                    log_message = f"{logic_name}: 온도 {sensors['temperature']}℃ ≥ {threshold}℃(외기온{sensors['out_temp']}℃ 보정)로 열림 시작"
                    
                elapsed = (current_time - self.start_time).total_seconds() * 1000
                if elapsed < config.get('action_time', 498000):
                    current_status = '498초열림'
                    result = {'status': current_status, 'code': 1}
                else:
                    if self.last_status != '100%열림':
                        log_message = f"{logic_name}: 498초 동작 완료, 100% 열림 상태"
                    self.start_time = None
                    current_status = '100%열림'
                    result = {'status': current_status, 'code': 1}
            else:
                if self.start_time or (self.last_status and '열림' in self.last_status):
                    log_message = f"{logic_name}: 온도 {sensors['temperature']}℃ < {threshold}℃로 닫힘"
                self.start_time = None
                current_status = '100%닫힘'
                result = {'status': current_status, 'code': 0}
                
        elif 2 <= section <= 4:
            current_status = '100%열림'
            if self.last_status != current_status:
                log_message = f"{logic_name}: 구간{section} 주간 모드로 100% 열림"
            result = {'status': current_status, 'code': 1}
            
        elif section == 5:
            config = curtain_config.get('5', {})
            threshold = config.get('threshold', 15)
            
            if sensors['temperature'] <= threshold:
                if not self.start_time:
                    self.start_time = current_time
                    log_message = f"{logic_name}: 온도 {sensors['temperature']}℃ ≤ {threshold}℃로 닫힘 시작"
                    
                elapsed = (current_time - self.start_time).total_seconds() * 1000
                if elapsed < config.get('action_time', 498000):
                    current_status = '498초닫힘'
                    result = {'status': current_status, 'code': 0}
                else:
                    if self.last_status != '100%닫힘':
                        log_message = f"{logic_name}: 498초 동작 완료, 100% 닫힘 상태"
                    self.start_time = None
                    current_status = '100%닫힘'
                    result = {'status': current_status, 'code': 0}
            else:
                if self.start_time or (self.last_status and '닫힘' in self.last_status):
                    log_message = f"{logic_name}: 온도 {sensors['temperature']}℃ > {threshold}℃로 열림"
                self.start_time = None
                current_status = '100%열림'
                result = {'status': current_status, 'code': 1}
        else:
            current_status = '보온100%'
            if self.last_status != current_status:
                log_message = f"{logic_name}: 구간{section} 야간 보온모드"
            result = {'status': current_status, 'code': 0}
        
        self.last_status = result['status']
        return result, log_message

class ShadeController:
    """차광스크린 제어"""
    def __init__(self):
        self.start_time = None
        self.stop_time = None
        self.state = 'idle'
        self.last_status = None
        
    def update(self, sensors, section, current_time, dat) -> Tuple[Dict, Optional[str]]:
        shade_config = RULES.get('SHADE_CONTROL', {})
        logic_name = f"차광스크린_구간{section}"
        log_message = None
        
        # 비 감지 처리
        if sensors['rain']:
            logic_name += "_비감지"
            rain_config = shade_config.get('rain_response', {})
            
            if not self.stop_time or (current_time - self.stop_time).total_seconds() * 1000 >= rain_config.get('wait_time', 60000):
                if self.state != 'rain_open':
                    self.start_time = current_time
                    self.stop_time = None
                    self.state = 'rain_open'
                    log_message = f"{logic_name}: 강우 감지로 비대응 열림 시작"
                    
            if self.start_time and self.state == 'rain_open':
                elapsed = (current_time - self.start_time).total_seconds() * 1000
                if elapsed < rain_config.get('action_time', 150000):
                    result = {'status': '비감지열림', 'code': 1}
                else:
                    if self.last_status == '비감지열림':
                        log_message = f"{logic_name}: 150초 동작 완료, 대기"
                    self.stop_time = current_time
                    self.start_time = None
                    self.state = 'idle'
                    result = {'status': '대기', 'code': 2}
            else:
                result = {'status': '대기', 'code': 2}
                
        # 일반 구간 처리
        elif section not in [3, 4]:
            logic_name += "_전구간열림"
            if self.last_status != '100%열림':
                log_message = f"{logic_name}: 구간{section} 기본 100% 열림"
            result = {'status': '100%열림', 'code': 1}
        else:
            # 섹션 3, 4 처리
            section_config = shade_config.get('section_3_4', {})
            duration = section_config.get('base_duration', 150000)
            
            # DAT >= 8 and 일사량 <= 50 시 지속시간 절반
            duration_modifier = ""
            if dat >= 8 and sensors['light'] <= 50:
                duration *= section_config.get('dat_8_light_50_multiplier', 0.5)
                duration_modifier = f"(DAT{dat}≥8, 일사량{sensors['light']}≤50으로 시간단축)"
                
            if section == 3:
                logic_name += "_일사량차광"
                light_threshold = section_config['section_3']['light_threshold']
                open_condition = sensors['light'] >= light_threshold
                position = section_config['section_3']['position']
                condition_text = f"일사량 {sensors['light']} ≥ {light_threshold}"
            else:  # section == 4
                logic_name += "_일사량열림"
                light_threshold = section_config['section_4']['light_threshold']
                open_condition = sensors['light'] <= light_threshold
                position = section_config['section_4']['position']
                condition_text = f"일사량 {sensors['light']} ≤ {light_threshold}"
                
            if open_condition:
                state_key = f'shade{section}'
                if (self.state != state_key or not self.start_time or 
                    (self.stop_time and (current_time - self.stop_time).total_seconds() * 1000 >= section_config.get('wait_after_action', 1800000))):
                    
                    if self.state != state_key:
                        log_message = f"{logic_name}: {condition_text}로 {position} 시작{duration_modifier}"
                    self.start_time = current_time
                    self.stop_time = None
                    self.state = state_key
                    
                if self.start_time and self.state == state_key:
                    elapsed = (current_time - self.start_time).total_seconds() * 1000
                    if elapsed < duration:
                        code = 0 if '차광' in position else 1
                        result = {'status': position, 'code': code}
                    else:
                        if self.last_status == position:
                            log_message = f"{logic_name}: {int(duration/1000)}초 동작 완료, 30분 대기"
                        self.stop_time = current_time
                        self.start_time = None
                        self.state = 'waiting'
                        result = {'status': '대기', 'code': 2}
            else:
                if self.last_status and self.last_status not in ['대기', '100%열림']:
                    log_message = f"{logic_name}: 조건 불만족으로 대기"
                result = {'status': '대기', 'code': 2}
        
        self.last_status = result['status']
        return result, log_message

class IrrigationController:
    """관수 제어"""
    def __init__(self):
        self.done = False
        
    def update(self, sensors, section, current_time, dat) -> Tuple[Dict, Optional[str]]:
        amounts = RULES.get('IRRIGATION_AMOUNTS', [])
        if section >= len(amounts):
            return {'status': '대기', 'code': 2}, None
            
        amount = amounts[section]
        irrigation_config = RULES.get('IRRIGATION_CONTROL', {})
        soil_threshold = irrigation_config.get('soil_moisture_threshold', 12.5)
        
        logic_name = f"관수_구간{section}"
        log_message = None
        
        if section == 1:
            logic_name += "_특별조건"
            special_config = irrigation_config.get('section_1_special', {})
            dat_threshold = special_config.get('dat_threshold', 7)
            sunrise_offset = special_config.get('sunrise_offset_hours', 1)
            
            # 일출 + 1시간 계산
            sunrise_time = datetime.strptime(sensors['sunrise'], '%H:%M').time()
            sunrise_plus_1 = datetime.combine(current_time.date(), sunrise_time) + timedelta(hours=sunrise_offset)
            
            should_irrigate = dat > dat_threshold or current_time >= sunrise_plus_1
            
            if (sensors['soil_moisture'] <= soil_threshold and amount > 0 and 
                should_irrigate and not self.done):
                self.done = True
                
                condition_reason = []
                if dat > dat_threshold:
                    condition_reason.append(f"DAT{dat}>7일")
                if current_time >= sunrise_plus_1:
                    condition_reason.append(f"일출+1시간({sunrise_plus_1.strftime('%H:%M')}) 경과")
                    
                log_message = f"{logic_name}: 토양수분 {sensors['soil_moisture']}% ≤ {soil_threshold}%, {'/'.join(condition_reason)}로 {amount}ml 관수"
                return {'status': f'{amount}ml관수', 'code': 1}, log_message
            else:
                return {'status': '대기', 'code': 2}, None
        else:
            if sensors['soil_moisture'] <= soil_threshold and amount > 0:
                log_message = f"{logic_name}: 토양수분 {sensors['soil_moisture']}% ≤ {soil_threshold}%로 {amount}ml 관수"
                return {'status': f'{amount}ml관수', 'code': 1}, log_message
            else:
                return {'status': '대기', 'code': 2}, None
                
    def reset_daily(self):
        """일일 리셋"""
        self.done = False

class FanController:
    """유동팬 제어"""
    def __init__(self):
        self.cycle = 0
        self.start_time = None
        self.stop_time = None
        self.last_status = None
        
    def update(self, sensors, section, current_time) -> Tuple[Dict, Optional[str]]:
        fan_config = RULES.get('FAN_CONTROL', {})
        logic_name = f"유동팬_구간{section}_온도차감지"
        log_message = None
        
        if section != fan_config.get('section', 8):
            if self.cycle > 0 or self.start_time or self.stop_time:
                log_message = f"{logic_name}: 구간{section}에서 비활성, 리셋"
            self.cycle = 0
            self.start_time = self.stop_time = None
            result = {'status': '대기', 'code': 2}
        else:
            temp_diff = abs(sensors['temp1'] - sensors['temp2'])
            diff_threshold = fan_config.get('temp_diff_threshold', 2)
            max_cycles = fan_config.get('max_cycles', 3)
            run_time = fan_config.get('run_time', 60000)  # ms
            wait_time = fan_config.get('wait_time', 300000)  # ms
            
            if temp_diff >= diff_threshold and self.cycle < max_cycles:
                if not self.start_time and not self.stop_time:
                    self.start_time = current_time
                    log_message = f"{logic_name}: 온도차 {temp_diff:.1f}℃ ≥ {diff_threshold}℃로 사이클{self.cycle+1} 시작"
                    result = {'status': '동작', 'code': 1}
                elif self.start_time:
                    elapsed = (current_time - self.start_time).total_seconds() * 1000
                    if elapsed < run_time:
                        result = {'status': '동작', 'code': 1}
                    else:
                        self.stop_time = current_time
                        self.start_time = None
                        log_message = f"{logic_name}: 사이클{self.cycle+1} 60초 동작 완료, 5분 대기"
                        result = {'status': '대기', 'code': 2}
                elif self.stop_time:
                    elapsed = (current_time - self.stop_time).total_seconds() * 1000
                    if elapsed < wait_time:
                        result = {'status': '대기', 'code': 2}
                    else:
                        self.stop_time = None
                        # 재측정
                        new_temp_diff = abs(sensors['temp1'] - sensors['temp2'])
                        if new_temp_diff >= diff_threshold:
                            self.cycle += 1
                            if self.cycle < max_cycles:
                                self.start_time = current_time
                                log_message = f"{logic_name}: 대기완료, 온도차 {new_temp_diff:.1f}℃로 사이클{self.cycle+1} 시작"
                                result = {'status': '동작', 'code': 1}
                            else:
                                log_message = f"{logic_name}: 최대 사이클{max_cycles} 완료"
                                result = {'status': '완료', 'code': 0}
                        else:
                            self.cycle = 0
                            log_message = f"{logic_name}: 온도차 {new_temp_diff:.1f}℃ < {diff_threshold}℃로 정상화"
                            result = {'status': '대기', 'code': 2}
            else:
                if temp_diff < diff_threshold and (self.cycle > 0 or self.start_time or self.stop_time):
                    log_message = f"{logic_name}: 온도차 {temp_diff:.1f}℃ < {diff_threshold}℃로 중지"
                self.cycle = 0
                self.start_time = self.stop_time = None
                result = {'status': '대기', 'code': 2}
        
        self.last_status = result['status']
        return result, log_message

class WindowController:
    """천창 제어 (상태 머신 패턴)"""
    def __init__(self):
        self.phase = 'idle'  # idle -> action -> wait
        self.next_action_time = None
        self.action_duration = 0
        self.last_status = None
        
    def update(self, sensors, section, current_time) -> Tuple[Dict, Optional[str]]:
        window_config = RULES.get('WINDOW_CONTROL', {})
        sections_config = window_config.get('sections', {})
        ctrl = sections_config.get(str(section))
        
        logic_name = f"천창_구간{section}_온도조건"
        log_message = None
        
        if not ctrl:
            self.phase = 'idle'
            return {'status': '대기', 'code': 2}, None

        temp_threshold = ctrl['temp_threshold']
        open_time = ctrl.get('open_time_sec', 0)
        close_time = ctrl.get('close_time_sec', 0)

        if self.phase == 'idle':
            condition = False
            action_type = ""
            
            if open_time > 0 and sensors['temperature'] >= temp_threshold:
                condition = True
                self.action_duration = open_time
                action_type = "열림"
                condition_text = f"온도 {sensors['temperature']}℃ ≥ {temp_threshold}℃"
            elif close_time > 0 and sensors['temperature'] <= temp_threshold:
                condition = True
                self.action_duration = close_time
                action_type = "닫힘"
                condition_text = f"온도 {sensors['temperature']}℃ ≤ {temp_threshold}℃"

            if condition:
                self.phase = 'action'
                self.next_action_time = current_time + timedelta(seconds=self.action_duration)
                log_message = f"{logic_name}: {condition_text}로 {action_type} {self.action_duration}초 시작"
                current_status = f'{action_type} 동작중'
                result = {'status': current_status, 'code': 1}
            else:
                current_status = '닫힘' if close_time > 0 else '대기'
                code = 0 if close_time > 0 else 2
                result = {'status': current_status, 'code': code}

        elif self.phase == 'action':
            if current_time < self.next_action_time:
                # 동작 중 - UI에만 남은 시간 표시, 로그는 기록하지 않음
                remain = int((self.next_action_time - current_time).total_seconds())
                action_type = "열림" if open_time > 0 else "닫힘"
                current_status = f'{action_type} 동작중'
                result = {'status': current_status, 'code': 1}
            else:
                self.phase = 'wait'
                wait_time = window_config.get('wait_time_ms', 300000)
                self.next_action_time = current_time + timedelta(milliseconds=wait_time)
                action_type = "열림" if open_time > 0 else "닫힘"
                log_message = f"{logic_name}: {action_type} {self.action_duration}초 완료, 5분 대기 후 재측정"
                current_status = f'{action_type} 완료'
                result = {'status': current_status, 'code': 2}

        elif self.phase == 'wait':
            if current_time < self.next_action_time:
                # 대기 중 - UI에만 남은 시간 표시, 로그는 기록하지 않음
                current_status = '재측정 대기중'
                result = {'status': current_status, 'code': 2}
            else:
                self.phase = 'idle'
                log_message = f"{logic_name}: 대기 완료, 조건 재측정"
                # 재측정을 위해 다시 update 호출
                return self.update(sensors, section, current_time)

        self.last_status = result['status']
        return result, log_message

class EnvironmentControlSystem:
    """통합 환경 제어 시스템"""
    def __init__(self):
        self.fog_controller = FOGController()
        self.fcu_controller = FCUController()
        self.co2_controller = CO2Controller()
        self.curtain_controller = CurtainController()
        self.shade_controller = ShadeController()
        self.irrigation_controller = IrrigationController()
        self.fan_controller = FanController()
        self.window_controller = WindowController()
        self.previous_states = {}
        self.last_valid_sensors = None
        
    def validate_sensors(self, sensors, current_time):
        """센서 검증 및 이전 유효값 사용"""
        valid_sensors = sensors.copy()
        has_invalid = False
        
        for key, value in sensors.items():
            if key not in ['sunrise', 'sunset', 'temp1', 'temp2']:
                if not validate_sensor(value, key):
                    has_invalid = True
                    if self.last_valid_sensors and key in self.last_valid_sensors:
                        valid_sensors[key] = self.last_valid_sensors[key]
                        
        if not has_invalid or not self.last_valid_sensors:
            self.last_valid_sensors = valid_sensors.copy()
            
        return valid_sensors
        
    def apply_control_logic(self, sensors, section, current_time, dat):
        """전체 제어 로직 적용"""
        # 센서 검증
        valid_sensors = self.validate_sensors(sensors, current_time)
        
        results = {}
        log_messages = []
        
        # 각 장치별 제어 로직 적용
        fog_result, fog_log = self.fog_controller.update(valid_sensors, section, current_time)
        results['fog'] = fog_result
        if fog_log: log_messages.append(('fog', fog_log))
        
        fcu_result, fcu_log = self.fcu_controller.update(valid_sensors, section, current_time)
        results['fcu'] = fcu_result
        if fcu_log: log_messages.append(('fcu', fcu_log))
        
        co2_result, co2_log = self.co2_controller.update(valid_sensors, section, current_time)
        results['co2'] = co2_result
        if co2_log: log_messages.append(('co2', co2_log))
        
        curtain_result, curtain_log = self.curtain_controller.update(valid_sensors, section, current_time)
        results['curtain'] = curtain_result
        if curtain_log: log_messages.append(('curtain', curtain_log))
        
        shade_result, shade_log = self.shade_controller.update(valid_sensors, section, current_time, dat)
        results['shade'] = shade_result
        if shade_log: log_messages.append(('shade', shade_log))
        
        irrigation_result, irrigation_log = self.irrigation_controller.update(valid_sensors, section, current_time, dat)
        results['irrigation'] = irrigation_result
        if irrigation_log: log_messages.append(('irrigation', irrigation_log))
        
        fan_result, fan_log = self.fan_controller.update(valid_sensors, section, current_time)
        results['fan'] = fan_result
        if fan_log: log_messages.append(('fan', fan_log))
        
        window_result, window_log = self.window_controller.update(valid_sensors, section, current_time)
        results['window'] = window_result
        if window_log: log_messages.append(('window', window_log))
        
        return results, log_messages
    
    def reset_daily_states(self):
        """일일 상태 리셋"""
        self.irrigation_controller.reset_daily()