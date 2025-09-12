# rules_runner.py
import os, time, requests
from datetime import datetime, date
from zoneinfo import ZoneInfo
from sqlalchemy import create_engine, text
from query import get_query
from rule_decider import load_rules, decide_rules
from SRSSCalc import SunriseCalculator
from log_db_handler import setup_logging

DB_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://admin:admin123@tsdb:5432/berrymind")
SUBMIT_URL = os.getenv("SCHEDULER_URL", "http://scheduler:8001/submit_schedules")
KST = ZoneInfo("Asia/Seoul")
cutoff = date(2025, 9, 22)

engine = create_engine(DB_URL, pool_pre_ping=True, pool_recycle=1800)
rules = load_rules("rules_conf")         # 규칙이 자주 바뀌면 이 줄을 함수 안으로 이동
calc = SunriseCalculator()

def run_once():
    with engine.connect() as conn:
        row = conn.execute(text(get_query())).first()
    if not row:
        logger.warning("No sensor row"); return
    res = dict(row._mapping)

    t = res["time"].astimezone(KST) if res["time"].tzinfo else res["time"].replace(tzinfo=KST)
    res["timeband"] = calc.get_timeband(t.strftime("%Y-%m-%d %H:%M:%S"))
    res["DAT"] = (t.date() - cutoff).days
    logger.info("[SENSOR] %s", res)

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
