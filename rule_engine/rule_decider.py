import json
from pathlib import Path
from typing import Dict, Any, List, Tuple, DefaultDict
from collections import defaultdict
from business_rules.variables import BaseVariables, numeric_rule_variable, select_rule_variable
from business_rules.actions   import BaseActions, rule_action
from business_rules.fields    import FIELD_TEXT, FIELD_NUMERIC
from business_rules.engine    import run_all

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
    def indoor_CO2(self) -> float:
        return float(self.vals.get("indoor_CO2", 0.0))

    @numeric_rule_variable(label="Water Content")
    def water_content(self) -> float:
        return float(self.vals.get("water_content", 0.0))

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
        "water_type": FIELD_TEXT,         # "WATER" or "NUTRIENT" (구동기: 양액기 고정)
        "duration_sec": FIELD_NUMERIC,    # 주입시간(sec)
        "pause_sec": FIELD_NUMERIC        # pause time(sec)
    })
    def nutsupply(self, water_type: str, duration_sec: int, pause_sec: int = 0):
        wt = water_type.upper()
        if wt not in ("WATER", "NUTRIENT"):
            wt = "NUTRIENT"  # 기본값 보정
        intent = {
            "actuator": "NUTRIENT_PUMP",  # 고정
            "water_type": wt,
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
                # 각 원소가 dict가 아니어도 사용처에 따라 허용할 수 있음
                return data  # type: ignore[return-value]
        except Exception:
            pass  # 로그를 쓰고 싶으면 여기서 print나 logger 사용
        return []

    if p.is_file():
        return _load_file(p)

    if p.is_dir():
        for fp in sorted(p.glob("*.json")):
            rules.extend(_load_file(fp))
        return rules

    # path가 존재하지 않으면 빈 리스트
    return []

def decide_rules(sensor_vals: Dict[str, Any], rules: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    구동기별로 가장 높은 priority의 트리거된 룰 1개를 선택해
    {actuator: {rule_name, priority, conditions, action}} 형태로 반환.
    """
    vars_ = EnvVars(sensor_vals)
    grouped: DefaultDict[str, List[Tuple[int, int, Dict[str, Any], Dict[str, Any], str]]] = defaultdict(list)
    # (priority, order_idx, conditions, action_intent, rule_name)

    for idx, rule in enumerate(rules):
        probe = ProbeActions()
        run_all(rule_list=[rule], defined_variables=vars_, defined_actions=probe, stop_on_first_trigger=True)
        if not probe.intents:
            continue
        for actuator, intent in probe.intents:  # 다액션 룰도 팬아웃
            grouped[actuator].append((
                int(rule.get("priority", 0)),
                idx,
                rule.get("conditions", {}),
                intent,                              # {"actuator","state","duration_sec","pause_sec"}
                rule.get("name", "")
            ))

    decisions: Dict[str, Any] = {}
    for actuator, cands in grouped.items():
        # priority 내림차순, 동일 priority면 먼저 등장한(rule order) 우선
        cands.sort(key=lambda x: (-x[0], x[1]))
        prio, _, conds, intent, name = cands[0]
        decisions[actuator] = {
            "rule_name": name,
            "priority": prio,
            "conditions": conds,
            "action": intent
        }
    return decisions

# 예시 실행
if __name__ == "__main__":
    sensor = {"indoor_temp": 31.2, "time_band": 2}
    rules  = load_rules("rules_conf")
    print(decide_rules(sensor, rules))
