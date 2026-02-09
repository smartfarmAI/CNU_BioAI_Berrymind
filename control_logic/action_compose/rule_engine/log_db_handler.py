import os, json, logging, traceback
from datetime import datetime, timezone
from sqlalchemy import create_engine, Table, MetaData

DB_URL   = os.getenv("DATABASE_URL", "postgresql+psycopg://admin:admin123@tsdb:5432/berrymind")
APP_NAME = os.getenv("APP_NAME", "rule_engine")

engine   = create_engine(DB_URL, pool_pre_ping=True, pool_recycle=1800)
app_logs = Table("app_logs", MetaData(), autoload_with=engine)  # DDL 없이 반사(reflect)

class SQLAlchemyPGHandler(logging.Handler):
    def __init__(self, engine, table, level=logging.INFO):
        super().__init__(level); self.engine, self.table = engine, table
    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            skip = {"name","msg","args","levelname","levelno","pathname","filename","module",
                    "exc_info","exc_text","stack_info","lineno","funcName","created",
                    "msecs","relativeCreated","thread","threadName","processName","process"}
            extra = {k:v for k,v in record.__dict__.items() if k not in skip} or None
            exc_text = "".join(traceback.format_exception(*record.exc_info)) if record.exc_info else None
            row = dict(
                ts=datetime.fromtimestamp(record.created, tz=timezone.utc),
                level=record.levelname,
                logger=record.name,             # 앱 이름으로 사용
                module=record.module,
                func=record.funcName,
                lineno=record.lineno,
                message=msg,
                extra=extra,
                exc_text=exc_text,
            )
            with self.engine.begin() as conn:
                conn.execute(self.table.insert().values(**row))
        except Exception:
            self.handleError(record)

def setup_logging(app_name: str = APP_NAME,
                  level_console=logging.DEBUG, level_db=logging.INFO) -> logging.Logger:
    root = logging.getLogger(); root.setLevel(logging.DEBUG)
    for h in list(root.handlers): root.removeHandler(h)
    ch = logging.StreamHandler(); ch.setLevel(level_console)
    ch.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
    root.addHandler(ch)
    dbh = SQLAlchemyPGHandler(engine, app_logs, level=level_db)
    dbh.setFormatter(logging.Formatter("%(message)s"))  # DB에는 본문만
    root.addHandler(dbh)
    return logging.getLogger(app_name)  # ← logger.name = 앱 이름

# 사용 예시
if __name__ == "__main__":
    logger = setup_logging()
    logger.info("boot OK")
    try:
        1/0
    except ZeroDivisionError:
        logger.exception("sample error")
