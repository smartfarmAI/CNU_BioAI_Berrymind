# fsm_server.py
import asyncio, os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from statemachine import DeviceFSM  # 네가 만든 FSM

# uvicorn fsm_server:app --reload --port 9000

# 액션 I/O 서버(네 mock_action_io) 주소
ACTION_IO_HOST = os.getenv("ACTION_IO_HOST","http://actionio:8000")

app = FastAPI(title="FSM Controller")

# 장치별 FSM 인스턴스 & 락
_devices: dict[str, DeviceFSM] = {}
_locks: dict[str, asyncio.Lock] = {}

def get_fsm(name: str) -> DeviceFSM:
    if name not in _devices:
        _devices[name] = DeviceFSM(host=ACTION_IO_HOST, actuator_name=name, verify_interval=1.0)
        _locks[name] = asyncio.Lock()
    return _devices[name]

# ---- 스키마 ----
class StartJobReq(BaseModel):
    cmd_name: str           # "OPEN" 같은 문자열
    duration_sec: int | None = 0
    ec: float | None = None
    ph: float | None = None    

class StartJobResp(BaseModel):
    opid: int
    state: str

class FSMStateResp(BaseModel):
    state: str
    want_opid: int | None
    deadline_ts: float
    last_state_code: int | None
    last_opid: int | None

# ---- 엔드포인트 ----
@app.post("/devices/{name}/jobs")
async def start_job(name: str, req: StartJobReq):
    fsm = get_fsm(name)
    print(f"{name} 요청이 들어왔습니다. req: {req}")
    async with _locks[name]:
        payload = req.model_dump(exclude_none=True)
        opid = await fsm.start_job(
            payload = payload
        )
        return opid

@app.get("/health")
def health():
    return {"ok": True}
