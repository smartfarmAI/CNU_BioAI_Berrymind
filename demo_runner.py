# demo_runner.py (핵심만)
import time, schedule
from sensor.sensor_mocking import SensorMock
from rule_engine.rule_decider import load_rules, decide_rules
from scheduler_component.scheduler_component import RuleScheduler, Plan

def send_cmd(actuator: str, state: str):
    print(f"[ACTUATOR_CMD] {actuator} -> {state}")

def main_loop():
    # 1) 센서 갱신
    sensor.tick()
    vals = sensor.values
    print("[SENSOR]", vals)

    # 2) 룰 결정 (구동기별 룰 이름만 반환)
    rules = load_rules("rule_engine/rules.json")
    chosen = decide_rules(vals, rules)
    print("[DECIDE]", chosen)

    # 3) 예시: 특정 룰 이름이 매칭되면 스케줄 계획 제출
    #    "온도 28 이상이면 1분 가동 → 30분 휴지 → 재체크(28 미만이면 STOP, 아니면 반복), time_band=2"
    if chosen.get("FCU") == "time_band 2 : FCU : ON : >= 30" and vals.get("time_band") == 2:
        plan = Plan(
            actuator="FCU",
            time_band=2,
            run_sec=60,
            pause_sec=1800,
            continue_if={"var":"avg_indoor_temp","op":">=","value":28},
            stop_if={"var":"avg_indoor_temp","op":"<","value":28},
            name=chosen["FCU"]
        )
        scheduler.submit(plan)
        
    print("[JOBS]", scheduler.list_jobs())
    print("[HIST-FCU]", scheduler.get_history("FCU")[-5:])   # 최근 5개만 보기
    print("[CYCLES]", dict(scheduler.cycles))

if __name__ == "__main__":
    # 센서
    sensor = SensorMock("sensor/conf.yaml")
    sensor.load(); sensor.tick()

    # 스케줄러
    scheduler = RuleScheduler(sensor_provider=lambda: sensor.values, send_cmd=send_cmd)
    scheduler.start()

    # 주기 평가(테스트는 1초 권장)
    schedule.every(1).seconds.do(main_loop)
    while True:
        schedule.run_pending()
        time.sleep(0.2)
