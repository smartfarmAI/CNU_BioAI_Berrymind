import streamlit as st
from datetime import datetime, timedelta
import time
from control_logic import (
    EnvironmentControlSystem, 
    determine_section, 
    validate_sensor
)

st.set_page_config(
    page_title='딸기 환경 제어 시뮬레이터',
    page_icon='🍓',
    layout='wide'
)

# 세션 상태 초기화
def init_session_state():
    if 'control_system' not in st.session_state:
        st.session_state.control_system = EnvironmentControlSystem()
    if 'current_time' not in st.session_state:
        st.session_state.current_time = datetime.now()
    if 'logs' not in st.session_state:
        st.session_state.logs = []
    if 'simulation_active' not in st.session_state:
        st.session_state.simulation_active = False
    if 'last_update' not in st.session_state:
        st.session_state.last_update = time.time()
    if 'speed_factor' not in st.session_state:
        st.session_state.speed_factor = 1
    if 'dat' not in st.session_state:
        st.session_state.dat = 1
    if 'manual_dat' not in st.session_state:
        st.session_state.manual_dat = True
    if 'elapsed_days' not in st.session_state:
        st.session_state.elapsed_days = 0
    if 'last_day' not in st.session_state:
        st.session_state.last_day = None
    # 시작 시간 상태 추가
    if 'start_time_setting' not in st.session_state:
        st.session_state.start_time_setting = datetime.now().time()

def add_log(device, message):
    """로그 추가 (가상 시간 전체 정보 포함)"""
    # 가상시간 전체 표시 (날짜 + 시간)
    virtual_time = st.session_state.current_time.strftime("%Y-%m-%d %H:%M:%S")
    
    # DAT 정보 추가
    current_dat = st.session_state.dat if st.session_state.manual_dat else st.session_state.dat + st.session_state.elapsed_days
    
    # 배속 정보
    speed_info = f"×{st.session_state.speed_factor}" if st.session_state.speed_factor > 1 else ""
    
    # 로그 엔트리 포맷: [가상시간 DAT배속정보] 메시지
    log_entry = f"[{virtual_time} DAT{current_dat}일{speed_info}] {message}"
    st.session_state.logs.append(log_entry)
    
    # 로그가 너무 많아지면 오래된 것 제거 (최대 1000개)
    if len(st.session_state.logs) > 1000:
        st.session_state.logs.pop(0)

def clear_logs():
    """로그 초기화"""
    st.session_state.logs = []
    add_log('시스템', '시스템_로그초기화: 시뮬레이션 시작으로 로그 초기화')

def get_sensor_values():
    """현재 입력된 센서값 반환"""
    return {
        'sunrise': st.session_state.get('sunrise', '06:30'),
        'sunset': st.session_state.get('sunset', '18:30'),
        'rain': st.session_state.get('rain', False),
        'temperature': st.session_state.get('temperature', 22.0),
        'humidity': st.session_state.get('humidity', 60.0),
        'co2': st.session_state.get('co2', 400),
        'light': st.session_state.get('light', 300),
        'wind_speed': st.session_state.get('wind_speed', 2.5),
        'out_temp': st.session_state.get('out_temp', 18.0),
        'soil_moisture': st.session_state.get('soil_moisture', 15.0),
        'temp1': st.session_state.get('temperature', 22.0),
        'temp2': st.session_state.get('temperature', 22.0) + 1
    }

def format_status_for_display(status):
    """상태 표시용 포맷팅 (남은 시간 정보 포함)"""
    if '동작중' in status:
        return status
    elif '대기중' in status:
        return status
    else:
        return status

def update_simulation():
    """시뮬레이션 업데이트"""
    if not st.session_state.simulation_active:
        return None, {}
    
    # 실시간 시간 계산
    current_real_time = time.time()
    delta_real = current_real_time - st.session_state.last_update
    st.session_state.last_update = current_real_time
    
    # 가상 시간 진행 (배속 적용)
    delta_virtual = timedelta(seconds=delta_real * st.session_state.speed_factor)
    st.session_state.current_time += delta_virtual
    
    # 날짜가 바뀌었는지 체크
    current_day = st.session_state.current_time.date()
    if st.session_state.last_day and current_day != st.session_state.last_day:
        st.session_state.elapsed_days += 1
        st.session_state.manual_dat = False
        st.session_state.control_system.reset_daily_states()  # 일일 상태 리셋
        add_log('시스템', f'시스템_일자변경: {current_day}로 날짜 변경, 경과일수: {st.session_state.elapsed_days}일, 일일 상태 리셋')
    st.session_state.last_day = current_day
    
    # 센서값 가져오기
    sensors = get_sensor_values()
    
    # 구간 결정
    section = determine_section(st.session_state.current_time, sensors['sunrise'], sensors['sunset'])
    
    # 현재 DAT 계산
    current_dat = st.session_state.dat if st.session_state.manual_dat else st.session_state.dat + st.session_state.elapsed_days
    
    # 제어 로직 적용
    control_results, log_messages = st.session_state.control_system.apply_control_logic(
        sensors, section, st.session_state.current_time, current_dat
    )
    
    # 상세 로그 메시지들 기록
    for device, message in log_messages:
        add_log(device, message)
    
    return section, control_results

def main():
    st.title('🍓 딸기 환경 제어 실시간 시뮬레이터 v2.1')
    st.markdown('**🔍 상세 제어 조건 로깅 및 가상시간 표시 버전**')
    
    init_session_state()
    
    # 사이드바 - 제어 패널
    with st.sidebar:
        st.header('⚙️ 시뮬레이션 제어')
        
        # 시뮬레이션 설정
        with st.expander('🎮 시뮬레이션 설정', expanded=True):
            # 시작 시간 설정 - session_state 사용으로 유지
            start_time = st.time_input(
                '시작 시간', 
                value=st.session_state.start_time_setting,
                help='시뮬레이션 시작 시 적용될 가상 시간'
            )
            # 변경된 시간을 session_state에 저장
            st.session_state.start_time_setting = start_time
            
            speed_options = [1, 10, 20, 30, 60, 3600]
            speed_labels = ['×1 (실시간)', '×10', '×20', '×30', '×60 (1분=1초)', '×3600 (1시간=1초)']
            speed_factor = st.selectbox(
                '시간 배속', 
                options=speed_options,
                format_func=lambda x: speed_labels[speed_options.index(x)],
                index=0
            )
            st.session_state.speed_factor = speed_factor
            
            # DAT 설정
            col1, col2 = st.columns(2)
            with col1:
                dat = st.number_input('DAT (정식 후 일수)', min_value=1, max_value=365, value=st.session_state.dat)
                st.session_state.dat = dat
            with col2:
                if st.button('수동 DAT', help='DAT를 수동으로 설정하면 날짜 자동 증가를 중지합니다'):
                    st.session_state.manual_dat = True
                    st.session_state.elapsed_days = 0
        
        # 현재 시간 설정 표시
        if not st.session_state.simulation_active:
            st.info(f'🕐 설정된 시작 시간: **{start_time.strftime("%H:%M")}**')
        
        # 제어 버튼들
        button_col1, button_col2 = st.columns(2)
        with button_col1:
            if st.button('▶️ 시작', use_container_width=True):
                st.session_state.simulation_active = True
                # 설정된 시작 시간을 사용
                st.session_state.current_time = datetime.combine(datetime.today(), start_time)
                st.session_state.last_update = time.time()
                st.session_state.last_day = st.session_state.current_time.date()
                st.session_state.manual_dat = True
                st.session_state.elapsed_days = 0
                
                # 제어 시스템 초기화
                st.session_state.control_system = EnvironmentControlSystem()
                clear_logs()
                add_log('시스템', f'시스템_시작: 시뮬레이션 시작 (배속: ×{speed_factor}, 시작시간: {start_time.strftime("%H:%M")})')
                st.rerun()
        
        with button_col2:
            if st.button('⏹️ 중지', use_container_width=True):
                st.session_state.simulation_active = False
                add_log('시스템', '시스템_중지: 사용자 요청으로 시뮬레이션 중지')
                st.rerun()
        
        # 시간 설정 버튼 추가
        if st.button('🕐 현재 시간으로 설정', use_container_width=True):
            current_time = datetime.now().time()
            st.session_state.start_time_setting = current_time
            st.success(f'시작 시간을 {current_time.strftime("%H:%M")}로 설정했습니다!')
            st.rerun()
        
        if st.button('🔄 센서값 즉시 적용', use_container_width=True):
            if st.session_state.simulation_active:
                sensors = get_sensor_values()
                section = determine_section(st.session_state.current_time, sensors['sunrise'], sensors['sunset'])
                current_dat = st.session_state.dat if st.session_state.manual_dat else st.session_state.dat + st.session_state.elapsed_days
                control_results, log_messages = st.session_state.control_system.apply_control_logic(
                    sensors, section, st.session_state.current_time, current_dat
                )
                # 즉시 적용 로그
                for device, message in log_messages:
                    add_log(device, message)
                add_log('센서', '센서_수동업데이트: 사용자 요청으로 센서값 즉시 반영')
                st.rerun()
            else:
                st.warning('⚠️ 시뮬레이션을 먼저 시작해주세요.')
        
        # 센서 입력 섹션
        st.header('📊 환경 센서 입력')
        
        with st.expander('🌅 시간 설정'):
            sunrise_time = st.time_input('일출 시간', value=datetime.strptime('06:30', '%H:%M').time())
            sunset_time = st.time_input('일몰 시간', value=datetime.strptime('18:30', '%H:%M').time())
            st.session_state.sunrise = sunrise_time.strftime('%H:%M')
            st.session_state.sunset = sunset_time.strftime('%H:%M')
        
        with st.expander('🌡️ 온도/습도'):
            st.session_state.temperature = st.number_input(
                '내부 온도 (°C)', 
                min_value=-20.0, max_value=80.0, value=22.0, step=0.1,
                help='내부 온도: -20°C ~ 80°C'
            )
            st.session_state.humidity = st.number_input(
                '내부 습도 (%)', 
                min_value=0.0, max_value=100.0, value=60.0, step=0.1,
                help='내부 습도: 0% ~ 100%'
            )
            st.session_state.out_temp = st.number_input(
                '외기온 (°C)', 
                min_value=-40.0, max_value=60.0, value=18.0, step=0.1,
                help='외기온: -40°C ~ 60°C'
            )
        
        with st.expander('🌱 대기/토양'):
            st.session_state.co2 = st.number_input(
                'CO₂ 농도 (ppm)', 
                min_value=0, max_value=2000, value=400,
                help='CO₂ 농도: 0 ~ 2000 ppm'
            )
            st.session_state.light = st.number_input(
                '일사량 (W/m²)', 
                min_value=0, max_value=1800, value=300,
                help='일사량: 0 ~ 1800 W/m²'
            )
            st.session_state.wind_speed = st.number_input(
                '풍속 (m/s)', 
                min_value=0.5, max_value=89.0, value=2.5, step=0.1,
                help='풍속: 0.5 ~ 89.0 m/s'
            )
            st.session_state.soil_moisture = st.number_input(
                '토양 함수율 (%vol)', 
                min_value=0.0, max_value=50.0, value=15.0, step=0.1,
                help='토양 함수율: 0 ~ 50 %vol'
            )
            st.session_state.rain = st.checkbox('☔ 강우 감지', help='강우 센서 상태')
    
    # 메인 영역
    main_col1, main_col2 = st.columns([3, 2])
    
    with main_col1:
        st.header('📈 실시간 장치 동작 상태')
        
        # 시뮬레이션 업데이트
        if st.session_state.simulation_active:
            section, control_results = update_simulation()
            current_dat = st.session_state.dat if st.session_state.manual_dat else st.session_state.dat + st.session_state.elapsed_days
        else:
            section = 1
            current_dat = st.session_state.dat
            # 기본 대기 상태
            control_results = {device: {'status': '대기', 'code': 2} for device in 
                             ['fog', 'fcu', 'co2', 'window', 'curtain', 'shade', 'irrigation', 'fan']}
        
        # 현재 상태 정보 (가상시간 전체 표시)
        info_cols = st.columns(4)
        with info_cols[0]:
            st.metric('📍 현재 구간', f'{section}구간')
        with info_cols[1]:
            # 가상시간 전체 정보 표시
            if st.session_state.simulation_active:
                virtual_datetime = st.session_state.current_time.strftime('%m-%d %H:%M:%S')
            else:
                virtual_datetime = st.session_state.start_time_setting.strftime('%H:%M') + ' (대기중)'
            st.metric('⏰ 가상 시간', virtual_datetime)
        with info_cols[2]:
            st.metric('🗓️ 정식 후 일수', f'{current_dat}일차')
        with info_cols[3]:
            status_color = '🟢' if st.session_state.simulation_active else '🔴'
            status_text = "실행중" if st.session_state.simulation_active else "중지됨"
            speed_text = f"×{st.session_state.speed_factor}" if st.session_state.speed_factor > 1 else ""
            st.metric('📊 시뮬레이션', f'{status_color} {status_text}{speed_text}')
        
        st.divider()
        
        # 장치별 상태 표시 (로직 이름 포함)
        device_info = {
            'fog': {'name': 'FOG 분무', 'icon': '💨', 'logic': f'FOG_구간{section}_온도기준'},
            'fcu': {'name': 'FCU 팬코일', 'icon': '❄️', 'logic': f'FCU_구간{section}_온도제어'},
            'co2': {'name': 'CO₂ 공급', 'icon': '🌿', 'logic': f'CO2_구간{section}_농도제어'},
            'window': {'name': '좌우천창', 'icon': '🪟', 'logic': f'천창_구간{section}_온도조건'},
            'curtain': {'name': '보온커튼', 'icon': '🏠', 'logic': f'보온커튼_구간{section}_온도제어'},
            'shade': {'name': '차광스크린', 'icon': '☂️', 'logic': f'차광스크린_구간{section}'},
            'irrigation': {'name': '관수시스템', 'icon': '💧', 'logic': f'관수_구간{section}'},
            'fan': {'name': '유동팬', 'icon': '🌪️', 'logic': f'유동팬_구간{section}_온도차감지'}
        }
        
        device_cols = st.columns(4)
        for i, (device_key, device_data) in enumerate(device_info.items()):
            col_idx = i % 4
            with device_cols[col_idx]:
                result = control_results.get(device_key, {'status': '대기', 'code': 2})
                status = format_status_for_display(result['status'])
                code = result['code']
                
                # 상태에 따른 색상 및 스타일
                if code == 1:  # 동작/열림
                    color = '🟢'
                    border_color = '#28a745'
                elif code == 0:  # 중지/닫힘
                    color = '🔴'
                    border_color = '#dc3545'
                else:  # 대기
                    color = '🟡'
                    border_color = '#ffc107'
                
                # 디바이스 상태 카드 (로직명 포함)
                st.markdown(f"""
                <div style="
                    border: 2px solid {border_color};
                    border-radius: 10px;
                    padding: 10px;
                    margin: 5px 0;
                    background-color: rgba(255,255,255,0.1);
                ">
                    <div style="font-size: 14px; font-weight: bold;">
                        {device_data['icon']} {device_data['name']}
                    </div>
                    <div style="font-size: 11px; color: #666; margin: 2px 0;">
                        {device_data['logic']}
                    </div>
                    <div style="font-size: 12px; margin-top: 5px;">
                        {color} {status}
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    with main_col2:
        st.header('📝 가상시간 포함 제어 로그')
        
        # 로그 다운로드 및 관리
        log_control_cols = st.columns(2)
        with log_control_cols[0]:
            if st.session_state.logs:
                log_text = '\n'.join(st.session_state.logs)
                st.download_button(
                    label='📥 로그 다운로드',
                    data=log_text,
                    file_name=f'virtual_time_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt',
                    mime='text/plain',
                    use_container_width=True
                )
        
        with log_control_cols[1]:
            if st.button('🗑️ 로그 지우기', use_container_width=True):
                clear_logs()
                st.rerun()
        
        # 로그 표시 영역
        log_container = st.container()
        with log_container:
            # 로그가 있으면 표시
            if st.session_state.logs:
                # 최근 로그부터 표시 (최대 100개)
                recent_logs = st.session_state.logs[-100:]
                log_text = '\n'.join(reversed(recent_logs))
                st.text_area(
                    '가상시간 포함 상세 로그',
                    value=log_text,
                    height=400,
                    disabled=True,
                    help='[가상날짜 가상시간 DAT배속] 로직명: 작동조건'
                )
                
                # 로그 통계
                st.caption(f'📊 총 로그 수: {len(st.session_state.logs)}개 (최근 100개 표시)')
                
                # 로그 예시
                if len(st.session_state.logs) > 0:
                    st.caption('🔍 **로그 형식 예시:**')
                    st.caption('`[2025-08-29 14:23:15 DAT15일×60] FOG_구간2_온도기준: 온도 26.5℃ ≥ 26℃로 분무 시작`')
            else:
                st.info('📋 시뮬레이션을 시작하면 가상시간 포함 상세 로그가 표시됩니다.')
                
                # 로그 형식 미리보기
                st.markdown("""
                **📝 로그 형식:**
                ```
                [가상날짜 가상시간 DAT일수일×배속] 로직명: 작동조건
                ```
                
                **예시:**
                ```
                [2025-08-29 14:23:15 DAT15일×60] FOG_구간2_온도기준: 온도 26.5℃ ≥ 26℃로 분무 시작
                [2025-08-29 14:24:15 DAT15일×60] FOG_구간2_온도기준: 60초 동작 완료, 10분 대기
                [2025-08-29 14:25:30 DAT15일×60] 천창_구간2_온도조건: 온도 22.1℃ ≥ 20℃로 열림 20초 시작
                ```
                """)
    
    # 하단 정보
    st.divider()
    with st.expander('ℹ️ 시뮬레이터 정보 v2.1 - 시작시간 설정 개선'):
        st.markdown("""
        ### 🍓 딸기 환경 제어 시뮬레이터 v2.1 - 시작시간 설정 개선
        
        **🕐 v2.1 시작시간 설정 개선사항:**
        - ✅ **시작시간 유지**: 설정한 시간이 리셋되지 않고 유지됩니다
        - ✅ **실시간 설정 표시**: 현재 설정된 시작시간을 명확하게 표시
        - ✅ **현재시간 설정 버튼**: 클릭 한 번으로 현재 시간으로 설정
        - ✅ **시뮬레이션 대기 표시**: 중지 상태에서도 설정된 시간 확인 가능
        
        **🕐 시작시간 설정 방법:**
        1. **수동 설정**: 시간 선택기로 원하는 시간 설정
        2. **현재시간 설정**: "🕐 현재 시간으로 설정" 버튼 클릭
        3. **시작 실행**: "▶️ 시작" 버튼 클릭으로 설정된 시간부터 시뮬레이션 시작
        
        **⚠️ 주의사항:**
        - 시뮬레이션 실행 중에는 시작시간 변경이 적용되지 않습니다
        - 새로운 시작시간을 적용하려면 중지 후 다시 시작해야 합니다
        
        **🔧 수정사항:**
        - `session_state.start_time_setting` 추가로 시작시간 상태 관리
        - `datetime.now().time()` 기본값 문제 해결
        - 시작시간 설정 상태 시각적 피드백 추가
        """)
    
    # 자동 새로고침 (시뮬레이션 활성화 시)
    if st.session_state.simulation_active:
        time.sleep(0.2)  # 200ms 간격
        st.rerun()

if __name__ == '__main__':
    main()