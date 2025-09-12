# 실행: uvicorn mock_action_io:app --reload --port 8000
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

# 단순 상태 저장소
READY, ERROR = 100, 900
WORKING, PREPARING, SUPPLYING, FINISHING = 201, 401, 402, 403
DB = {}  # name -> {"opid": int, "state_code": int, "next_opid": int}

def ensure(name: str):
    DB.setdefault(name, {"opid": 0, "state_code": READY, "next_opid": 1})
    return DB[name]

class SendReq(BaseModel):
    cmd_name: str
    duration_sec: int = 0

class SetReq(BaseModel):
    opid: int | None = None
    state_code: int | None = None

@app.get("/actuators/{name}/get_state")
def get_state(name: str):
    st = ensure(name)
    print(f"/actuators/{name}/get_state 요청 들어옴. \n opid {st['opid']}, state_code {st['state_code']}")
    return {"opid": st["opid"], "state_code": st["state_code"]}

@app.post("/actuators/{name}/send_command")
def send_command(name: str, req: SendReq):
    st = ensure(name)
    print(f"/actuators/{name}/send_command 요청 들어옴 param : {req}")
    opid = st["next_opid"]
    st["next_opid"] += 1
    st["state_code"] = 201
    st["opid"] = opid
    return {"opid": opid}

@app.post("/actuators/{name}/set")
def set_state(name: str, req: SetReq):
    st = ensure(name)
    print(f"셋팅전 값 \n {name} : {st['state_code']}")
    if req.opid is not None:
        st["opid"] = req.opid
    if req.state_code is not None:
        st["state_code"] = req.state_code
    return {"ok": True, "opid": st["opid"], "state_code": st["state_code"]}

