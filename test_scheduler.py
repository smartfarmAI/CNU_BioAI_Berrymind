import requests
from datetime import datetime, timedelta
import pandas as pd
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from rule_engine.rule_decider import load_rules, decide_rules
from util.SRSSCalc import SunriseCalculator

# Scheduler app endpoint
SCHEDULER_URL = "http://localhost:8001/submit_schedules"

def get_test_data():
    """Load test data from CSV and prepare sensor values"""
    df = pd.read_csv("test_sample.csv")
    first_row = df.iloc[0]
    
    # Initialize sunrise calculator with sample coordinates
    calculator = SunriseCalculator(35.8, 127.1)
    
    return {
        'time_band': calculator.get_timeband(first_row["저장시간"]),
        'indoor_temp': first_row["내부온도(1)"],
        'indoor_humidity': first_row["내부습도(1)"],
        'rain': first_row["감우"],
        'wind_speed': first_row["풍속"],
        'temp_diff': 2,
        'outdoor_temp': first_row["외부온도"],
        'solar_radiation': first_row["외부일사"],
        'DAT': 7,
        'indoor_CO2': first_row["CO2농도(1)"],
        'water_content': 12
    }

def create_fcu_plan():
    """Create a scheduling plan for FCU based on test data"""
    test_data = get_test_data()
    rules = load_rules("rule_engine/rules_conf")
    decisions = decide_rules(test_data, rules)
    
    fcu_decision = decisions.get('FCU', {})
    if not fcu_decision:
        print("No FCU decision made with the test data")
        return None
    
    # Convert the decision to the format expected by the scheduler
    action_name = fcu_decision.get('action', 'off')
    duration_sec = fcu_decision.get('duration_sec', 60)
    
    return {
        "items": {
            "FCU": {
                "action_name": action_name,
                "action_param": {
                    "duration_sec": duration_sec
                }
            }
        },
        "run_at": (datetime.now() + timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S")
    }

def test_scheduler():
    """Test the scheduler by submitting an FCU plan"""
    plan = create_fcu_plan()
    if not plan:
        return
    
    print("Scheduling FCU action:", plan)
    
    try:
        response = requests.post(SCHEDULER_URL, json=plan)
        if response.status_code == 200:
            print("Successfully scheduled FCU action")
            print("Scheduled to run at:", plan["run_at"])
            print("Action details:", plan["items"]["FCU"])
        else:
            print(f"Failed to schedule. Status code: {response.status_code}")
            print("Response:", response.text)
    except Exception as e:
        print(f"Error scheduling FCU action: {str(e)}")

if __name__ == "__main__":
    print("Make sure the scheduler app is running on port 8001")
    print("Run: uvicorn scheduler_component.scheduler_app:app --reload --port 8001")
    test_scheduler()