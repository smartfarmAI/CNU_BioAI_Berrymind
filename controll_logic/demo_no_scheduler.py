import time, schedule
from mock_sensor.sensor_mocking import SensorMock
from rule_engine.rule_decider import load_rules, decide_rules

def main_loop(sensor: SensorMock, rules_path: str):
    # 1) 센서 tick → 새로운 값 생성
    sensor.tick()
    vals = sensor.values
    print(f"[SENSOR] {vals}")

    # 2) 룰 불러오기
    rules = load_rules(rules_path)

    # 3) 룰 결정
    decision = decide_rules(vals, rules)
    print(f"[DECISION] {decision}")

if __name__ == "__main__":
    # 센서 준비
    sensor = SensorMock("mock_sensor/conf.yaml")
    sensor.load()

    rules_path = "rule_engine/rules_conf"

    # 최초 1회 실행
    main_loop(sensor, rules_path)

    # 1분마다 실행
    # schedule.every(1).minutes.do(main_loop, sensor=sensor, rules_path=rules_path)
    schedule.every(1).seconds.do(main_loop, sensor=sensor, rules_path=rules_path)
    
    while True:
        schedule.run_pending()
        time.sleep(1)
