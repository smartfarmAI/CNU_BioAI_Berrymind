from sqlalchemy import create_engine, text
from query import get_query
import os
from rule_decider import load_rules, decide_rules

db_url = os.environ.get("DATABASE_URL")

engine = create_engine(db_url)

# 센서값 받아옴
with engine.connect() as conn:
    res = conn.execute(text(get_query()))
    row = res.first()
    res = dict(row._mapping) if row else None


rules  = load_rules("rules_conf")
print(decide_rules(res, rules))