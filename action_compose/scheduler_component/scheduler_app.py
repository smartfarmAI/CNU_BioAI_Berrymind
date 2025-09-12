# 실행: uvicorn scheduler_app:app --reload --port 8001
from fastapi import FastAPI
from pydantic import BaseModel
from scheduler_component import PlanScheduler, compile_plan, PlanItem
from typing import Any, Dict
from datetime import datetime
from zoneinfo import ZoneInfo
import requests,os

app = FastAPI()

FSM_HOST_BASE = os.getenv("FSM_HOST_BASE","http://fsm:9000/devices")

class Plan(BaseModel):
    items: Dict[str,PlanItem]
    run_at: str | None = None

def dispatch_fn(actuator: str, item: PlanItem):
    # 리퀘스트 보냄 /devies/{actuator}/jobs {"cmd_name": "string", "duration_sec": 0}
    res = requests.post(url=f"{FSM_HOST_BASE}/{actuator}/jobs",json={"cmd_name":item.action_param["state"],"duration_sec": item.action_param["duration_sec"]})
    return res
    # print(f"[DISPATCH] {actuator} -> {item.action_name} {item.action_param}")

ps = PlanScheduler(dispatch_fn, debounce_sec=0)

@app.post("/submit_schedules")
def submit_schedule(plan: Plan):
    print(plan)
    if plan.run_at:
        dt = datetime.strptime(plan.run_at, "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZoneInfo("Asia/Seoul"))
    else:
        dt = None
    ps.submit_plan(plan=compile_plan(plan.items),run_at = dt)


@app.get("/get_schedules")
def get_schedule():
    return [ (j.id, j.next_run_time) for j in ps.sched.get_jobs() ]

@app.get("/health")
def health(): return {"status": "ok"}