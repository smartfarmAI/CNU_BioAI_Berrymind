from apscheduler.schedulers.blocking import BlockingScheduler
from client import ExtraClient
import os, json
import asyncio
from datetime import datetime
from sqlalchemy import create_engine, text
import json, ast

DB_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://admin:admin123@tsdb:5432/berrymind")
engine = create_engine(DB_URL, pool_pre_ping=True, pool_recycle=1800)

# Load configuration from conf.json
try:
    conf_path = "conf.json"
    with open(conf_path) as f:
        config = json.load(f)
except FileNotFoundError:
    print("Error: conf.json not found. Please make sure the configuration file exists.")
except json.JSONDecodeError:
    print("Error: Could not decode conf.json. Please check the file format.")

# Create an instance of ExtraClient
client = ExtraClient(config)


def get_image_job():
    # Test get_image for each dataid
    if client.dataids:
        for data_id in client.dataids:
            try:
                print(f"Getting image for data_id: {data_id}...")
                result = asyncio.run(client.get_image(data_id=data_id))
                print(f"Image for data_id {data_id} received and saved to {result['image_path']}")
                print(f"Image filename: {result['filename']}")
            except Exception as e:
                if "404" in str(e) or "No image found" in str(e):
                    print(f"No image found for data_id {data_id} (this is expected if no images are uploaded yet)")
                elif "400" in str(e) or "Invalid image path" in str(e):
                    print(f"Invalid image path for data_id {data_id} (database entry exists but file is missing)")
                else:
                    print(f"Error getting image for data_id {data_id}: {e}")
    else:
        print("No dataids_for_camera found in the configuration file.")
    

def get_forecast_job():
    # Create forecasts directory if it doesn't exist
    if not os.path.exists("forecasts"):
        os.makedirs("forecasts")

    # Test get_forecast
    try:
        print("Getting forecast data...")
        asyncio.run(client.get_forecast())
        print("Forecast data received and saved to forecasts/forecast.json")
        # You can uncomment the line below to print the forecast data
        # print(json.dumps(forecast, indent=4))
    except Exception as e:
        print(f"Error getting forecast: {e}")

def _md_escape(s: str) -> str:
    return str(s).replace("|", r"\|").replace("\n", " ").replace("\r", " ")

def _msgparsor(s: str) -> str:
    if not s.startswith("[DECISION]"):
        return s

    # 본문(객체) 시작 위치
    i = s.find("{")
    if i < 0:
        return s
    body = s[i:]

    # JSON → 실패 시 literal 파싱
    try:
        obj = json.loads(body)
    except json.JSONDecodeError:
        try:
            obj = ast.literal_eval(body)
        except Exception:
            return s

    if not isinstance(obj, dict):
        return s

    # 각 구동기의 action_param만 남기기
    pruned = {
        actuator: spec.get("action_param")
        for actuator, spec in obj.items()
        if isinstance(spec, dict) and "action_param" in spec
    }

    # 문자열(JSON)로 변환 + 접두어 복원
    return "[DECISION] " + json.dumps(pruned, ensure_ascii=False, separators=(",", ":"))

def post_heartbeat_job():
    # health check 호출하기 스케쥴러는 등록된 스케쥴도
    # 거른 센서값
    # 룰
    # 스케쥴러 등록 결과
    # 상태머신에서 보내진 결과
    # 액션 io 에서 보낸 결과
    try:
        with engine.connect() as conn:
            rows = (
                conn.execute(
                    text("SELECT ts, logger, message FROM app_logs ORDER BY id DESC LIMIT 3;")
                ).mappings().all()
            )

        header = [
            "# Heartbeat",
            f"_generated: {datetime.now()}_",
            "",
            "| ts | logger | message |",
            "|---|---|---|",
        ]
        body = [
            f"| {r['ts']} "
            f"| {_md_escape(r['logger'])} | {_md_escape(_msgparsor(r['message']))} |"
            for r in rows
        ] or ["_no recent logs_"]

        md = "\n".join(header + body)
        print(md)
        asyncio.run(client.post_heartbeat(content=md))
    except Exception as e:
        print(f"Error posting heartbeat: {e}", flush=True)



sched = BlockingScheduler()

# 이미지 오전 10시 , 15시
sched.add_job(get_image_job, "cron", hour=10, minute=5)
sched.add_job(get_image_job, "cron", hour=15, minute=5)

# 기상 3시간 마다
sched.add_job(get_forecast_job, "interval", hours=3, next_run_time=datetime.now())
sched.add_job(post_heartbeat_job, "interval", minutes=5, next_run_time=datetime.now())

sched.start()
