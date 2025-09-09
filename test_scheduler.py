import os
import sys
import json
import time
import random
import requests
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Add the project root to the Python path so relative imports work when run from repo root
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rule_engine.rule_decider import load_rules, decide_rules
from util.SRSSCalc import SunriseCalculator

SCHEDULER_URL = "http://localhost:8001/submit_schedules"
TZ = ZoneInfo("Asia/Seoul")

# 완주군 이서면 농생명로 100
LATITUDE = 35.8
LONGITUDE = 127.1

CSV_PATH = "test_sample.csv"


def row_to_sensor_vals(row, calculator: SunriseCalculator):
    """Mirror test_real_data.py mapping for a single pandas row -> sensor values dict."""
    # '저장시간'이 문자열/타임스탬프 어떤 형식이든 get_timeband가 처리하도록 그대로 전달
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
            'indoor_CO2': row["CO2농도(1)"], 
            'water_content': random.choice([10,11,12,13,14])
        }
    return vals


def find_fcu_decision_from_csv(csv_path: str) -> dict | None:
    """Scan test_sample.csv, run rule_engine, and return the first FCU decision found."""
    df = pd.read_csv(csv_path)
    calc = SunriseCalculator(LATITUDE, LONGITUDE)
    rules = load_rules("rule_engine/rules_conf")

    # Iterate rows to find one that triggers FCU
    for i, row in df.iterrows():
        try:
            vals = row_to_sensor_vals(row, calc)
            decisions = decide_rules(vals, rules)
            fcu = decisions.get("FCU")
            if fcu:
                print(f"[HIT] Row {i} triggers FCU: time_band={vals['time_band']}, indoor_temp={vals['indoor_temp']}, "
                      f"indoor_humidity={vals['indoor_humidity']}")
                print("[FCU Decision]", json.dumps(fcu, ensure_ascii=False))
                return fcu
        except KeyError as e:
            # If any required column missing, raise a clear error
            raise KeyError(f"CSV missing required column: {e}. Check headers in {csv_path}.") from e
        except Exception as e:
            # Continue scanning even if a row has an issue
            print(f"[WARN] Skipping row {i} due to: {e}")
            continue
    return None


def schedule_fcu_action(run_after_minutes: int = 1):
    """Pick FCU decision from CSV and schedule it via scheduler_app.
       - OFF  : now + run_after_minutes (default 1)
       - ON   : now
    """
    fcu_decision = find_fcu_decision_from_csv(CSV_PATH)
    if not fcu_decision:
        print("[ERROR] No FCU decision could be derived from the CSV and rules. Aborting.")
        return

    # Build plan for only FCU
    item = {
        "action_name": fcu_decision["action_name"],
        "action_param": fcu_decision["action_param"],
    }

    # state 확인 (없으면 즉시 실행으로 간주)
    state = str(fcu_decision.get("action_param", {}).get("state", "")).upper()

    now_kst = datetime.now(tz=TZ)
    if state == "OFF":
        run_at_dt = now_kst + timedelta(minutes=run_after_minutes)
    else:
        # ON 또는 기타 값/누락 → 즉시
        run_at_dt = now_kst

    plan = {
        "items": {"FCU": item},
        "run_at": run_at_dt.strftime("%Y-%m-%d %H:%M:%S"),
    }

    print(f"[POST] Scheduling FCU to run at (KST): {plan['run_at']}  (state={state})")
    print("[POST] Payload:", json.dumps(plan, ensure_ascii=False))

    resp = requests.post(SCHEDULER_URL, json=plan, timeout=10)
    print(f"[RESP] Status: {resp.status_code}")
    try:
        print("[RESP] Body:", resp.json())
    except Exception:
        print("[RESP] Body (text):", resp.text)


if __name__ == "__main__":
    print("NOTE: Ensure the scheduler app is running:")
    print("      uvicorn scheduler_component.scheduler_app:app --reload --port 8001\n")
    schedule_fcu_action(run_after_minutes=1)
