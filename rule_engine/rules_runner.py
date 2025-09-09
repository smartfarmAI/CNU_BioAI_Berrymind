from sqlalchemy import create_engine, text
from query import get_query
import os
from rule_decider import load_rules, decide_rules
from SRSSCalc import SunriseCalculator
from datetime import date

db_url = os.environ.get("DATABASE_URL")

engine = create_engine(db_url)

# 센서값 받아옴
with engine.connect() as conn:
    res = conn.execute(text(get_query()))
    row = res.first()
    res = dict(row._mapping) if row else None

# 센서값에 timeband, DAT 추가
calculator = SunriseCalculator()
res["timeband"] = calculator.get_timeband(res["time"].strftime("%Y-%m-%d %H:%M:%S"))
cutoff = date(2025, 9, 22) # 정식일
res["DAT"] = max((res["time"] - cutoff).days, 0)
print(res)

rules  = load_rules("rules_conf")
print(decide_rules(res, rules))