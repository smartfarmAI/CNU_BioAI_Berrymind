import time, schedule, random
from action_compose.rule_engine.rule_decider import load_rules, decide_rules
from util.SRSSCalc import SunriseCalculator
import pandas as pd

def main_loop():
    i, row = next(rows)
    
    vals = {
            'time_band': calculator.get_timeband(row["저장시간"]), 
            'indoor_temp': row["내부온도(1)"], 
            'indoor_humidity': row["내부습도(1)"], 
            'rain': row["감우"], 
            'wind_speed': row["풍속"], 
            'temp_diff': 2, 
            'outdoor_temp': row["외부온도"], 
            'solar_radiation': row["외부일사"], 
            'DAT': random.choice([0,4,7,11]), 
            'indoor_co2': row["CO2농도(1)"], 
            'soil_water_content': random.choice([10,11,12,13,14])
        }
    print("[SENSOR]", vals)

    rules = load_rules("rule_engine/rules_conf")
    decisions = decide_rules(vals, rules)               # {'FCU': {...}, 'CO2': {...}}
    print("[DECISION]", decisions)

if __name__ == "__main__":
    # 완주군 이서면 농생명로 100 좌표
    LATITUDE = 35.8
    LONGITUDE = 127.1
    calculator = SunriseCalculator(LATITUDE, LONGITUDE)

    df = pd.read_csv("test_sample.csv")
    rows = df.iterrows()  # 제너레이터

    while rows:
        main_loop()