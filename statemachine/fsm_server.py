import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional
from statemachine import DeviceFSM  # FSM client

# uvicorn fsm_server:app --reload --port 9000

ACTION_IO_HOST = "http://localhost:8000"

app = FastAPI(title="FSM Controller")

# 장치별 FSM 인스턴스 & 락
_devices: Dict[str, DeviceFSM] = {}
_locks: Dict[str, asyncio.Lock] = {}

def get_fsm(name: str) -> DeviceFSM:
    if name not in _devices:
        _devices[name] = DeviceFSM(host=ACTION_IO_HOST, actuator_name=name, verify_interval=1.0)
        _locks[name] = asyncio.Lock()
    return _devices[name]

# ---- 스키마 ----
class StartReq(BaseModel):
    cmd_name: str
    duration_sec: Optional[int] = 0

class StartJobResp(BaseModel):
    opid: int
    state: str

class FSMStateResp(BaseModel):
    state: str
    want_opid: Optional[int]
    deadline_ts: float
    last_state_code: Optional[int]
    last_opid: Optional[int]

# ---- 엔드포인트 ----
@app.post("/devices/{name}/jobs", response_model=StartJobResp)
async def start_job(name: str, req: StartReq):
    fsm = get_fsm(name)
    async with _locks[name]:
        # 1) FSM이 READY가 아닐 때: 액션 IO에서 남은시간 조회 후 409
        if fsm.state != "READY":
            remain = None
            try:
                st = await asyncio.to_thread(fsm._read_state)  # {"opid","state_code","remain*_sec"}
                remain = (
                    st.get("remaining_sec", None)
                    if "remaining_sec" in st else
                    st.get("remain_sec", st.get("remain", None))
                )
                if remain is not None:
                    remain = int(remain)
            except Exception:
                remain = None
            msg = f"busy (state={fsm.state}"
            if remain is not None:
                msg += f", remaining={remain}s"
            msg += ")"
            raise HTTPException(status_code=409, detail=msg)

        # 2) FSM 사전점검 내장: IO READY 아닐 시 RuntimeError 발생 → 409로 변환
        try:
            opid = await fsm.start_job(req.cmd_name, req.duration_sec or 0)
        except RuntimeError as e:
            reason = str(e)
            if reason in {"preflight_not_ready", "preflight_read_failed"}:
                try:
                    st = await asyncio.to_thread(fsm._read_state)
                    remain = (
                        st.get("remaining_sec", None)
                        if "remaining_sec" in st else
                        st.get("remain_sec", st.get("remain", None))
                    )
                    if remain is not None:
                        remain = int(remain)
                except Exception:
                    remain = None
                msg = f"not_ready (io_state={fsm.last_state_code}"
                if remain is not None:
                    msg += f", remaining={remain}s"
                msg += ")"
                raise HTTPException(status_code=409, detail=msg)
            # 그 외 예외는 그대로 전파
            raise

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
