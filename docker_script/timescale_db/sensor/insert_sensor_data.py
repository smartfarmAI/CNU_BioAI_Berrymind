from datetime import datetime, timezone
from sqlalchemy import create_engine, text
import os

db_url = os.environ.get("DATABASE_URL")

# 호스트=localhost / 컨테이너=timescaledb
engine = create_engine(db_url)

def insert_greenhouse2(rows: list[dict]):
    if not rows: return
    cols = sorted({k for r in rows for k in r.keys()})
    named = ",".join(f":{c}" for c in cols)
    colnames = ",".join(cols)
    stmt = text(f"INSERT INTO greenhouse2 ({colnames}) VALUES ({named})")
    with engine.begin() as conn:
        conn.execute(stmt, rows)

if __name__ == "__main__":
    insert_greenhouse2([{
        "time": datetime.now(timezone.utc),
        "out_temp": 24.3, "in_co2": 420.0, "fcu_status": 1
    }])
    print("ok")