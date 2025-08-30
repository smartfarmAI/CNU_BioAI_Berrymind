import json
from typing import Dict, Any, List, Tuple, DefaultDict
from collections import defaultdict
from business_rules.variables import BaseVariables, numeric_rule_variable
from business_rules.actions   import BaseActions, rule_action
from business_rules.fields    import FIELD_TEXT
from business_rules.engine    import run_all

# 1) Variables
class EnvVars(BaseVariables):
    def __init__(self, vals: Dict[str, Any]): self.vals = vals
    @numeric_rule_variable(label="Average Indoor Temp")
    def avg_indoor_temp(self) -> float: return float(self.vals.get("avg_indoor_temp", 0.0))
    @numeric_rule_variable(label="Time Band")
    def time_band(self) -> float: return float(self.vals.get("time_band", 0))

# 2) ProbeActions: 이름형(fcu_on/off) + 파라미터형(set_state) 모두 지원
class ProbeActions(BaseActions):
    def __init__(self): self.actions: List[Tuple[str, str]] = []  # (ACTUATOR, STATE)
    # 이름형: FCU 전용 (필요 시 다른 구동기도 같은 패턴으로 추가)
    @rule_action()
    def fcu_on(self):  self.actions.append(("FCU", "ON"))
    @rule_action()
    def fcu_off(self): self.actions.append(("FCU", "OFF"))
    # 파라미터형(선택): {"name":"set_state","params":{"actuator":"FCU","state":"ON"}}
    @rule_action(params={"actuator": FIELD_TEXT, "state": FIELD_TEXT})
    def set_state(self, actuator: str, state: str):
        self.actions.append((actuator.upper(), state.upper()))

def load_rules(path="rules.json") -> list:
    with open(path, "r", encoding="utf-8") as f: return json.load(f)

def decide_rules(sensor_vals: Dict[str, Any], rules: list) -> Dict[str, str]:
    """
    구동기별로 priority가 가장 높은 '룰 이름'만 선택해 반환.
    반환 예: {"FCU": "time_band 2 : FCU : ON : >= 30"}
    """
    vars_ = EnvVars(sensor_vals)
    grouped: DefaultDict[str, List[Tuple[int, str]]] = defaultdict(list)  # actuator -> [(prio, rule_name)]

    for rule in rules:
        probe = ProbeActions()
        run_all(rule_list=[rule], defined_variables=vars_, defined_actions=probe, stop_on_first_trigger=True)
        if probe.actions:
            actuator, _ = probe.actions[0]  # 룰당 액션 1개 가정
            grouped[actuator].append((int(rule.get("priority", 0)), rule.get("name", "")))

    decisions: Dict[str, str] = {}
    for actuator, cands in grouped.items():
        cands.sort(key=lambda x: x[0], reverse=True)
        decisions[actuator] = cands[0][1]
    return decisions

# 예시 실행
if __name__ == "__main__":
    sensor = {"avg_indoor_temp": 31.2, "time_band": 2}
    rules  = load_rules("rules.json")
    print(decide_rules(sensor, rules))
