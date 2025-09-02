# demo_runner.py (핵심만)
import time, schedule
from sensor.sensor_mocking import SensorMock
from rule_engine.rule_decider import load_rules, decide_rules
from scheduler_component.scheduler_component import PlanScheduler, compile_plan, PlanItem, Plan

# 상태머신 대신: 테스트용 디스패치(스케줄러만 검증)
def dispatch_fn(actuator: str, item: PlanItem):
    print(f"[DISPATCH] {actuator} -> {item.action_name} {item.action_param}")

def main_loop():
    sensor.tick()
    vals = sensor.values
    print("[SENSOR]", vals)

    rules = load_rules("rule_engine/rules_conf")
    decisions = decide_rules(vals, rules)               # {'FCU': {...}, 'CO2': {...}}
    print("[DECISION]", decisions)

    plan = compile_plan(decisions)                      # Plan(items={act: PlanItem(...)})

    ps.submit_plan(plan)                                # 스케줄 등록(디듀프/퍼즈/전역 디바운스 적용)

    # 잡 확인(필요 시)
    jobs = [ (j.id, j.next_run_time) for j in ps.sched.get_jobs() ]
    print("[JOBS]", jobs)

if __name__ == "__main__":
    sensor = SensorMock("sensor/conf.yaml")
    sensor.load()
    sensor.tick()
    ps = PlanScheduler(dispatch_fn, debounce_sec=0)     # 전역 디바운스 0초(원하면 높이기)
    schedule.every(1).seconds.do(main_loop)             # 1초 주기 테스트
    while True:
        schedule.run_pending()
        time.sleep(0.2)
