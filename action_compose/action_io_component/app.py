# 실행: uvicorn app:app --reload --port 8000
from fastapi import FastAPI, HTTPException
from factory import load_conf, build_client, build_actuator
from actuator_base import Command
from ksconstants import CMDCODE
from pydantic import BaseModel

app = FastAPI()
CONF = load_conf()
CLIENT = build_client(CONF["connect"]["host"],int(CONF["connect"]["port"]))
ACTS = {name: build_actuator(name, CLIENT, reg) for name, reg in CONF["devices"].items()}

@app.get("/actuators/{name}/get_state")
def get_state(name: str):
    try:
        return ACTS[name].read_state()
    except KeyError:
        raise HTTPException(404, f"unknown actuator: {name}")

class CommandIn(BaseModel):
    name: str
    duration_sec: int  = 0
    # 추가 파라미터가 필요한 장치는 라우트 분리 or 쿼리파라미터로 처리

@app.post("/actuators/{name}/send_command")
def post_command(name: str, body: CommandIn):
    try:
        act = ACTS[name]
    except KeyError:
        raise HTTPException(404, f"unknown actuator: {name}")
    print(body)
    # 장치별 추가 인자 처리
    if name in {"SKY_WINDOW_LEFT","SKY_WINDOW_RIGHT","SHADING_SCREEN","HEAT_CURTAIN"}:
        opid = act.send(Command(name=CMDCODE[body.name], duration_sec=body.duration_sec or 0))
    elif name == "NUTRIENT_PUMP":
        opid = act.send(Command(name=CMDCODE[body.name], duration_sec=body.duration_sec or 0))
    else:
        opid = act.send(Command(name=CMDCODE[body.name], duration_sec=body.duration_sec or 0))
    return {"opid": opid}

@app.get("/health")
def health():
    return {"ok": True}