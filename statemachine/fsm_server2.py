# fsm_server.py
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from statemachine import DeviceFSM  # 네가 만든 FSM

# uvicorn fsm_server:app --reload --port 9000

# 액션 I/O 서버(네 mock_action_io) 주소
ACTION_IO_HOST = "http://localhost:8000"

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
    async with _locks[name]:
        if fsm.state != "READY": #ready가 아닐경우 409초
            #남은 시간(초) 포함 메시지
            import time as _t
            remain = None
            try:
                if getattr(fsm, "deadline_ts", 0) > 0:
                    remain = max(0, int(getattr(fsm, "deadline_ts", 0) - _t.time()))
            except Exception:
                remain = None
            msg = f"busy (state={fsm.state}"
            if remain is not None:
                msg += f", remaining={remain}s"
            msg += ")"
            raise HTTPException(status_code=409, detail=msg)
        opid = await fsm.start_job(
            cmd_name=req.cmd_name,
            duration_sec=req.duration_sec
        )
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
