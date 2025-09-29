from apscheduler.schedulers.blocking import BlockingScheduler
from client import ExtraClient
import os, json, yaml, joblib
import asyncio
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
import json, ast
from pathlib import Path
from get_X_prod_sql import get_X_sql
from data_prep.registry import REGISTRY
import data_prep.rules  # 필수: 룰 등록
import pandas as pd
import numpy as np
from calc_vpd import vpd_kpa

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

TARGETS = ["after_30min_indoor_co2","after_30min_indoor_humidity","after_30min_indoor_temp"]

cfg = yaml.safe_load(open("conf/base.yaml"))
models, features = {}, {}
for t in TARGETS:
    d = Path(f"lgbm_models/model_{t}")
    mp, fp = d / f"{t}.pkl", d / "features.txt"
    if mp.exists():
        models[t] = joblib.load(mp)
        with open(fp) as f:
            features[t] = [ln.strip() for ln in f if ln.strip()]
    
def predict_job(): 
    with engine.connect() as conn:   
        test_x = pd.read_sql(get_X_sql(), conn)

    if test_x.empty:
        return  # 이번 턴 스킵

    # 시간 컬럼이 있을 때만 TZ 변환
    if "time" in test_x.columns and pd.api.types.is_datetime64_any_dtype(test_x["time"]):
        test_x["time"] = test_x["time"].dt.tz_convert("Asia/Seoul")

    # DB에 넣을 값
    insert_data= dict()

    # id 문자열(필요 시)
    if "id" in test_x.columns:
        idxs = ",".join(test_x["id"].astype(str))
        insert_data["idxs"] = idxs

    # 전처리
    fn = REGISTRY["r4_min_max_delta_slope_inference"]
    out = fn(test_x, cfg)  # ['set_id','time',<features...>]

    for t in TARGETS:
        if t not in models:              # 모델 없으면 스킵
            print(f"❌ 모델 없음: {t} (스킵)")
            continue

        feats = features[t]
        pred_X = out.drop(columns=["time"] + TARGETS, errors="ignore").copy()
        for c in feats:
            if c not in pred_X.columns:
                pred_X[c] = 0.0
        pred_X = pred_X[feats]

        preds = models[t].predict(pred_X)
        insert_data[t] = float(preds)
        clipped = np.clip(preds, cfg["post"]["bounds"][t]["min"], cfg["post"]["bounds"][t]["max"])
        insert_data[f"clipped_{t}"] = float(clipped)

    insert_data["vpd"] = float(vpd_kpa(temp_c=insert_data["clipped_after_30min_indoor_temp"],rh_percent=insert_data["clipped_after_30min_indoor_humidity"]))

    with engine.begin() as conn:
        conn.execute(
            text("""
            INSERT INTO predictions (
                idxs,
                after_30min_indoor_co2,
                after_30min_indoor_humidity,
                after_30min_indoor_temp,
                clipped_after_30min_indoor_co2,
                clipped_after_30min_indoor_humidity,
                clipped_after_30min_indoor_temp,
                vpd
            )
            VALUES (
                :idxs,
                :after_30min_indoor_co2,
                :after_30min_indoor_humidity,
                :after_30min_indoor_temp,
                :clipped_after_30min_indoor_co2,
                :clipped_after_30min_indoor_humidity,
                :clipped_after_30min_indoor_temp,
                :vpd
            )
            """),
            insert_data
        )
    # 목표제어발행
    target_time = (datetime.now() + timedelta(minutes=35)).isoformat(timespec='seconds')
    targets = {
                    "farm_id": 1,
                    "temperature": insert_data["clipped_after_30min_indoor_temp"],
                    "humidity": insert_data["clipped_after_30min_indoor_humidity"],
                    "CO2": insert_data["clipped_after_30min_indoor_co2"],
                    "VPD": insert_data["vpd"],
                    "targettime": target_time
                }
    asyncio.run(client.post_target([targets]))

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

def _safe(s):  # _md_escape 대체용 (이미 있으면 이건 지워도 됨)
    return s.replace("|", "\\|").replace("`", "\\`") if isinstance(s, str) else s

def _fmt_num(x, nd=3):
    if x is None:
        return "—"
    try:
        return f"{float(x):.{nd}f}"
    except Exception:
        return str(x)
    
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
            # 1) 최근 로그 3개
            rows = (
                conn.execute(
                    text("SELECT ts, logger, message FROM app_logs ORDER BY id DESC LIMIT 3;")
                ).mappings().all()
            )

            # 2) 35분 이전의 가장 최근 예측 1행
            pred = conn.execute(text("""
                SELECT   created_at
                    , after_30min_indoor_co2
                    , after_30min_indoor_humidity
                    , after_30min_indoor_temp
                    , clipped_after_30min_indoor_co2
                    , clipped_after_30min_indoor_humidity
                    , clipped_after_30min_indoor_temp
                    , vpd
                FROM predictions
                WHERE created_at <= NOW() - INTERVAL '35 minutes'
                ORDER BY created_at DESC, id DESC
                LIMIT 1;
            """)).mappings().first()

        header_logs = [
            "",
            "### Recent logs",
            "",
            "| ts | logger | message |",
            "|---|---|---|",
        ]
        body_logs = [
            f"| {r['ts']} | {_safe(r['logger'])} | {_safe(_msgparsor(r['message']))} |"
            for r in rows
        ] or ["_no recent logs_"]

        # 2) 예측 표
        header_pred = [
            "",
            "### Latest prediction (<= now-35m)",
            "",
            "| created_at | co2 | humidity | temp | clipped_co2 | clipped_humidity | clipped_temp | vpd |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
        if pred:
            created = pred["created_at"]
            created_str = (
                created.isoformat(timespec="seconds")
                if hasattr(created, "isoformat") else str(created)
            )
            body_pred = [(
                f"| {created_str}"
                f" | {_fmt_num(pred['after_30min_indoor_co2'])}"
                f" | {_fmt_num(pred['after_30min_indoor_humidity'])}"
                f" | {_fmt_num(pred['after_30min_indoor_temp'])}"
                f" | {_fmt_num(pred['clipped_after_30min_indoor_co2'])}"
                f" | {_fmt_num(pred['clipped_after_30min_indoor_humidity'])}"
                f" | {_fmt_num(pred['clipped_after_30min_indoor_temp'])}"
                f" | {_fmt_num(pred['vpd'])} |"
            )]
        else:
            body_pred = ["_no eligible predictions (<= now-35m)_"]

        md = "\n".join(header_logs + body_logs + header_pred + body_pred)
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

sched.add_job(predict_job, "interval", minutes=1, next_run_time=datetime.now())

sched.start()

