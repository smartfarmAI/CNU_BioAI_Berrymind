# rules_runner.py
import os, time, requests
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from sqlalchemy import create_engine, text
from query import get_query
from rule_decider import load_rules, decide_rules
from SRSSCalc import SunriseCalculator
from log_db_handler import setup_logging

DB_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://admin:admin123@tsdb:5432/berrymind")
SUBMIT_URL = os.getenv("SCHEDULER_URL", "http://scheduler:8001/submit_schedules")
KST = ZoneInfo("Asia/Seoul")
cutoff = date(2025, 9, 18)

engine = create_engine(DB_URL, pool_pre_ping=True, pool_recycle=1800)
rules = load_rules("rules_conf")         # 규칙이 자주 바뀌면 이 줄을 함수 안으로 이동
calc = SunriseCalculator()

#관수이벤트를 위한 변수
last_daily = None

def run_once():
    with engine.connect() as conn:
        row = conn.execute(text(get_query())).first()
    if not row:
        logger.warning("No sensor row"); return
    res = dict(row._mapping)

    t = res["time"].astimezone(KST) if res["time"].tzinfo else res["time"].replace(tzinfo=KST)
    res["time_band"] = calc.get_timeband(t.strftime("%Y-%m-%d %H:%M:%S"))
    dat = (t.date() - cutoff).days
    res["DAT"] = dat
    logger.info("[SENSOR] %s", res)

    """
    매일 SR+1시간에 120초간 관수

    급액 EC와 pH는 아래와 같은 수치를 따름

    DAT ~7 EC 0.8, pH 5.5
    DAT 8 -30 EC 1.0, pH 5.5
    DAT 31 -60 EC 1.2, pH 5.5
    DAT 61- EC 1.4, pH 5.5
    """
    global last_daily
    today = date.today()
    if last_daily != today:
        last_daily = today
        sr, _ = calc.calculate_sunrise_sunset(today.strftime("%Y%m%d"))
        nut_event_t = datetime.strptime(datetime.today().strftime("%Y-%m-%d ") + sr, "%Y-%m-%d %H:%M") + timedelta(hours=1)
        ec = 0.8
        if dat <= 7:
            ec =  0.8
        elif 8 <= dat <= 30:
            ec = 1.0
        elif 31 <= dat <= 60:
            ec = 1.2
        else:  # dat >= 61
            ec = 1.4
        params = {
            "items": {
                "NUTRIENT_PUMP": {
                    "action_name": "nutsupply",
                    "action_param": {"state":"NUT_WATER","duration_sec":120, "ec":ec, "ph":5.5}
                }
            },
            "run_at": nut_event_t.strftime("%Y-%m-%d %H:%M:%S")
        }
        r = requests.post(SUBMIT_URL, json=params, timeout=5)


    decision = decide_rules(res, rules)
    logger.info("[DECISION] %s", decision)

    r = requests.post(SUBMIT_URL, json={"items": decision}, timeout=5)
    r.raise_for_status()
    logger.info("[SUBMIT] %s %s", r.status_code, r.text[:200])

if __name__ == "__main__":
    logger = setup_logging()
    while True:
        try:
            run_once()
        except Exception as e:
            logger.exception("rules_runner failed: %s", e)
        now = datetime.now(KST)
        sleep = 60 - now.second - now.microsecond/1e6
        time.sleep(max(1.0, sleep))
