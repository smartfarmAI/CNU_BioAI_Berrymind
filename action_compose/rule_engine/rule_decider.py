import json
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple, DefaultDict
from collections import defaultdict
from business_rules.variables import BaseVariables, numeric_rule_variable, select_rule_variable
from business_rules.actions   import BaseActions, rule_action
from business_rules.fields    import FIELD_TEXT, FIELD_NUMERIC
from business_rules.engine    import run_all

# =========================
# WINDOW-ONLY STATE / HELPERS
# =========================
_WINDOW_LAST_EXEC_TS: Dict[str, float] = {}  # key: SKY_WINDOW_LEFT | SKY_WINDOW_RIGHT

# 데드밴드(경계 흔들림 방지): 315–360, 0–45, 135–225
_WIN_DEADBAND_RANGES = [(315, 360), (0, 45), (135, 225)]
_LAST_WIND_SECTOR: str = ""  # 'LOW'(0-180) | 'HIGH'(180-360)

def _win_in_deadband(deg: float) -> bool:
    return any(lo <= deg <= hi for lo, hi in _WIN_DEADBAND_RANGES)

def _win_sector(deg: float) -> str:
    return 'LOW' if 0 <= deg < 180 else 'HIGH'

def _stabilize_wdir(raw_deg: float) -> float:
    """데드밴드에서는 직전 섹터 유지(LOW→90°, HIGH→270°로 클램프)."""
    global _LAST_WIND_SECTOR
    if not _LAST_WIND_SECTOR:
        _LAST_WIND_SECTOR = _win_sector(raw_deg)
        return raw_deg
    if _win_in_deadband(raw_deg):
        return 90.0 if _LAST_WIND_SECTOR == 'LOW' else 270.0
    _LAST_WIND_SECTOR = _win_sector(raw_deg)
    return raw_deg

def _cooldown_ok(actuator: str, pause_sec: int) -> bool:
    last = _WINDOW_LAST_EXEC_TS.get(actuator, 0.0)
    return (time.time() - last) >= max(0, pause_sec)

def _mark_fired(actuator: str) -> None:
    _WINDOW_LAST_EXEC_TS[actuator] = time.time()

def _is_windward(actuator: str, wdir_deg: float) -> bool:
    # 오른쪽창: 0–180 풍상 / 180–360 풍하
    # 왼쪽창  : 0–180 풍하 / 180–360 풍상
    if actuator == "SKY_WINDOW_RIGHT":
        return 0 <= wdir_deg < 180
    if actuator == "SKY_WINDOW_LEFT":
        return 180 <= wdir_deg < 360
    return False

def _is_open_state(s: str) -> bool:
    s = (s or "").upper()
    return s in ("OPEN", "TIMED_OPEN")

# 1) Variables
class EnvVars(BaseVariables):
    def __init__(self, vals: Dict[str, Any]): self.vals = vals
    
    @numeric_rule_variable(label="Indoor Temp")
    def indoor_temp(self) -> float: return float(self.vals.get("indoor_temp", 0.0))
    
    @numeric_rule_variable(label="Time Band")
    def time_band(self) -> float: return float(self.vals.get("time_band", 0))

    @numeric_rule_variable(label="Indoor Humidity")
    def indoor_humidity(self) -> float:
        return float(self.vals.get("indoor_humidity", 0.0))

    @numeric_rule_variable(label="Rain")
    def rain(self) -> int:
        return int(self.vals.get("rain", 0))

    @numeric_rule_variable(label="Wind Speed")
    def wind_speed(self) -> float:
        return float(self.vals.get("wind_speed", 0.0))

    # === 추가: 풍향 ===
    @numeric_rule_variable(label="Wind Direction")
    def wind_direction(self) -> float:
        return float(self.vals.get("wind_direction", 0.0))

    @numeric_rule_variable(label="Temp Diff")
    def temp_diff(self) -> float:
        return float(self.vals.get("temp_diff", 0.0))

    @numeric_rule_variable(label="Outdoor Temp")
    def outdoor_temp(self) -> float:
        return float(self.vals.get("outdoor_temp", 0.0))

    @numeric_rule_variable(label="Solar Radiation")
    def solar_radiation(self) -> float:
        return float(self.vals.get("solar_radiation", 0.0))

    @numeric_rule_variable(label="DAT")
    def DAT(self) -> int:
        return int(self.vals.get("DAT", 0))

    @numeric_rule_variable(label="Indoor CO2")
    def indoor_co2(self) -> float:
        return float(self.vals.get("indoor_co2", 0.0))

    @numeric_rule_variable(label="Soil Water Content")
    def soil_water_content(self) -> float:
        return float(self.vals.get("soil_water_content", 0.0))

# 2) ProbeActions
class ProbeActions(BaseActions):
    def __init__(self): self.intents: List[Tuple[str, str]] = []  
    
    @rule_action(params={
        "actuator": FIELD_TEXT,           # 스위치류 구동기 명
        "state": FIELD_TEXT,              # "ON" or "OFF"
        "duration_sec": FIELD_NUMERIC,    # 동작시간(sec)
        "pause_sec": FIELD_NUMERIC        # pause time(sec)
    })
    def switch_action(self, actuator: str, state: str, duration_sec: int=0, pause_sec: int=0):
        intent = {
            "actuator": actuator.upper(),
            "state": state.upper(),
            "duration_sec": int(duration_sec),
            "pause_sec": int(pause_sec)
        }
        self.intents.append((intent["actuator"], intent))
    
    
    @rule_action(params={
        "state": FIELD_TEXT,         # "WATER" or "NUTRIENT" (구동기: 양액기 고정)
        "duration_sec": FIELD_NUMERIC,    # 주입시간(sec)
        "pause_sec": FIELD_NUMERIC        # pause time(sec)
    })
    def nutsupply(self, state: str, duration_sec: int = 0, pause_sec: int = 0):
        state = state.upper()
        intent = {
            "actuator": "NUTRIENT_PUMP",  # 고정
            "state": state,
            "duration_sec": duration_sec,
            "pause_sec": pause_sec
        }
        self.intents.append((intent["actuator"], intent))

    
    @rule_action(params={
        "actuator": FIELD_TEXT,           # 개폐류 구동기
        "state": FIELD_TEXT,              # "OPEN" or "CLOSE"
        "temp_diff": FIELD_NUMERIC,       # 기준 temp_diff
        "duration_sec": FIELD_NUMERIC,    # 개폐시간(sec)
        "pause_sec": FIELD_NUMERIC        # pause time(sec)
    })
    def vent_action(self, actuator: str, state: str, temp_diff: float = 0, duration_sec: float = 0, pause_sec: float = 0):
        intent = {
            "actuator": actuator.upper(),
            "state": state.upper(),
            "temp_diff": float(temp_diff),
            "duration_sec": int(duration_sec),
            "pause_sec": int(pause_sec)
        }
        self.intents.append((intent["actuator"], intent))


def load_rules(path: str = "rules_conf") -> List[Dict[str, Any]]:
    """
    - path가 파일이면: 그 파일의 리스트(JSON 배열)만 반환
    - path가 디렉토리면: *.json 파일을 모두 읽어 리스트를 합쳐 반환
    - 각 파일은 JSON 배열이어야 함. (아니면 스킵)
    """
    p = Path(path)
    rules: List[Dict[str, Any]] = []

    def _load_file(fp: Path) -> List[Dict[str, Any]]:
        try:
            with fp.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
        except Exception:
            pass
        return []

    if p.is_file():
        return _load_file(p)

    if p.is_dir():
        for fp in sorted(p.glob("*.json")):
            rules.extend(_load_file(fp))
        return rules

    return []

def decide_rules(sensor_vals: Dict[str, Any], rules: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    구동기별로 가장 높은 priority의 트리거된 룰 1개를 선택해
    {actuator: {rule_name, priority, conditions, action}} 형태로 반환.

    WINDOW PATCH:
      - 풍향 데드밴드 안정화(센서 복사본에만 적용)
      - SKY_WINDOW_* 한정 pause_sec(쿨다운) 적용
      - 동시 개방 시 '풍하 먼저, 풍상 나중' → 같은 싸이클에선 풍상 억제
    """
    # --- 창 규칙을 위해 풍향만 안정화(센서 원본은 보존) ---
    sv = dict(sensor_vals)
    if "wind_direction" in sv:
        try:
            sv["wind_direction"] = _stabilize_wdir(float(sv["wind_direction"]))
        except Exception:
            pass

    vars_ = EnvVars(sv)
    grouped: DefaultDict[str, List[Tuple[int, int, Dict[str, Any], Dict[str, Any], str, str]]] = defaultdict(list)
    
    for idx, rule in enumerate(rules):
        probe = ProbeActions()
        run_all(rule_list=[rule], defined_variables=vars_, defined_actions=probe, stop_on_first_trigger=True)
        if not probe.intents:
            continue
        action_name = rule.get("actions", [{}])[0].get("name", "")
        
        for actuator, intent in probe.intents:  # 다액션 룰도 팬아웃
            grouped[actuator].append((
                int(rule.get("priority", 0)),
                idx,
                rule.get("conditions", {}),
                intent,                              # {"actuator","state","duration_sec","pause_sec"}
                rule.get("name", ""),
                action_name
            ))

    # 1차: 각 창/비창별 후보 선정(창은 쿨다운 통과하는 첫 후보)
    win_candidates: Dict[str, Dict[str, Any]] = {}
    decisions: Dict[str, Any] = {}

    for actuator, cands in grouped.items():
        cands.sort(key=lambda x: (-x[0], x[1]))
        is_window = actuator in {"SKY_WINDOW_LEFT", "SKY_WINDOW_RIGHT"}

        if not is_window:
            prio, _, conds, intent, name, action_name = cands[0]
            decisions[actuator] = {
                "rule_name": name,
                "priority": prio,
                "conditions": conds,
                "action_name": action_name,
                "action_param": intent
            }
            continue

        # 창: pause_sec 쿨다운 적용
        pick = None
        for prio, _, conds, intent, name, action_name in cands:
            if _cooldown_ok(actuator, int(intent.get("pause_sec", 0))):
                pick = (prio, conds, intent, name, action_name)
                break
        if pick is None:
            # 쿨다운 미통과 → 첫 후보를 그대로 알림(실행은 안 함)
            prio, _, conds, intent, name, action_name = cands[0]
            decisions[actuator] = {
                "rule_name": f"{name} (cooldown)",
                "priority": prio,
                "conditions": conds,
                "action_name": action_name,
                "action_param": intent,
                "cooldown_until": _WINDOW_LAST_EXEC_TS.get(actuator, 0.0) + int(intent.get("pause_sec", 0))
            }
        else:
            prio, conds, intent, name, action_name = pick
            win_candidates[actuator] = {
                "rule_name": name,
                "priority": prio,
                "conditions": conds,
                "action_name": action_name,
                "action_param": intent
            }

    # 2차: 창 두 장치 동시 개방 시 → 풍하 우선, 풍상 억제
    if win_candidates:
        wdir = float(sv.get("wind_direction", 0.0))
        L = win_candidates.get("SKY_WINDOW_LEFT")
        R = win_candidates.get("SKY_WINDOW_RIGHT")

        if L:  # 기본은 모두 반영
            decisions["SKY_WINDOW_LEFT"] = L
        if R:
            decisions["SKY_WINDOW_RIGHT"] = R

        if L and R:
            sL = L["action_param"].get("state", "")
            sR = R["action_param"].get("state", "")
            if _is_open_state(sL) and _is_open_state(sR):
                left_is_windward  = _is_windward("SKY_WINDOW_LEFT", wdir)
                right_is_windward = _is_windward("SKY_WINDOW_RIGHT", wdir)
                # 풍하 먼저 → 풍상(바람 맞는 쪽)은 이번 싸이클 억제
                if left_is_windward and not right_is_windward:
                    # LEFT=풍상 → R만 실행
                    decisions.pop("SKY_WINDOW_LEFT", None)
                elif right_is_windward and not left_is_windward:
                    # RIGHT=풍상 → L만 실행
                    decisions.pop("SKY_WINDOW_RIGHT", None)

        # 실행으로 채택된 창은 타임스탬프 갱신
        for a in ("SKY_WINDOW_LEFT", "SKY_WINDOW_RIGHT"):
            if a in decisions and "(cooldown)" not in decisions[a]["rule_name"]:
                _mark_fired(a)

    return decisions


# 예시 실행
if __name__ == "__main__":
    sensor = {"indoor_temp": 31.2, "time_band": 2, "wind_direction": 170}
    rules  = load_rules("rules_conf")
    print(decide_rules(sensor, rules))
