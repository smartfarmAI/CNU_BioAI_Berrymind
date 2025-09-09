from sqlalchemy import create_engine, text
from query import get_query
import os

db_url = os.environ.get("DATABASE_URL")

engine = create_engine(db_url)


with engine.connect() as conn:
    res = conn.execute(text(get_query()))
    row = res.first()
    res = dict(row._mapping) if row else None

print(res)