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
        _devices[name] = DeviceFSM(host=ACTION_IO_HOST, actuator_name=name, verify_interval=3.0)
        _locks[name] = asyncio.Lock()
    return _devices[name]

# ---- 스키마 ----
class StartJobReq(BaseModel):
    cmd_name: str           # "OPEN" 같은 문자열
    duration_sec: int | None = 0

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
@app.post("/devices/{name}/jobs", response_model=StartJobResp)
async def start_job(name: str, req: StartJobReq):
    fsm = get_fsm(name)
    print(f"{name} 요청이 들어왔습니다. req: {req}")
    async with _locks[name]:
        if fsm.state != "READY":
            print(f"{name} 기존 요청 처리중으로 거부되었습니다.")
            return StartJobResp(opid=-1, state=fsm.state)
            # raise HTTPException(status_code=409, detail=f"busy (state={fsm.state})")
        print(f"{name} fsm.start_job을 시작합니다.")
        opid = await fsm.start_job(
            cmd_name=req.cmd_name,
            duration_sec=req.duration_sec
        )
        print(f"{name} {opid} 시작되었습니다.")
        return StartJobResp(opid=opid, state=fsm.state)

@app.get("/devices/{name}/state", response_model=FSMStateResp)
async def get_state(name: str):
    fsm = get_fsm(name)
    return FSMStateResp(
        state=fsm.state,
        want_opid=getattr(fsm, "want_opid", None),
        deadline_ts=getattr(fsm, "deadline_ts", 0.0),
        last_state_code=getattr(fsm, "last_state_code", None),
        last_opid=getattr(fsm, "last_opid", None),
    )

@app.post("/devices/{name}/reset")
async def reset(name: str):
    fsm = get_fsm(name)
    fsm.reset()
    return {"ok": True, "state": fsm.state}

@app.get("/health")
def health():
    return {"ok": True}
