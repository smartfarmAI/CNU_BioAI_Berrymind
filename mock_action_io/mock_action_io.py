# 실행: uvicorn mock_action_io:app --reload --port 8000
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, Dict, Any
from time import time
from math import ceil

app = FastAPI()

# 상태 코드 (장치와 합의된 값)
READY, ERROR = 100, 900
WORKING = 201

# name -> 상태
DB: Dict[str, Dict[str, Any]] = {}

def ensure(name: str) -> Dict[str, Any]:
    DB.setdefault(name, {"opid": 0, "state_code": READY, "next_opid": 1, "started_ts": None, "end_ts": None})
    return DB[name]

class SendReq(BaseModel):
    cmd_name: str
    duration_sec: int = 0

class SetReq(BaseModel):
    opid: Optional[int] = None
    state_code: Optional[int] = None
    remain_sec: Optional[int] = None  # 남은시간 직접 세팅(테스트 용)

@app.get("/actuators/{name}/get_state")
def get_state(name: str):
    st = ensure(name)
    now = time()
    # 진행 중이면 남은 시간 계산 및 상태 업데이트
    remain = 0
    if st.get("end_ts"):
        remain = max(0, int(ceil(st["end_ts"] - now)))
        if remain == 0:
            # 작업 종료
            st["state_code"] = READY
            st["started_ts"] = None
            st["end_ts"] = None
    return {"opid": st["opid"], "state_code": st["state_code"], "remain_sec": remain}

@app.post("/actuators/{name}/send_command")
def send_command(name: str, req: SendReq):
    st = ensure(name)
    opid = st["next_opid"]
    st["next_opid"] += 1

    # duration 기반 작업 생성
    now = time()
    if req.duration_sec and req.duration_sec > 0:
        st["started_ts"] = now
        st["end_ts"] = now + int(req.duration_sec)
        st["state_code"] = WORKING
        remain = int(req.duration_sec)
    else:
        # duration==0이면 즉시 완료 취급
        st["started_ts"] = None
        st["end_ts"] = None
        st["state_code"] = READY
        remain = 0

    st["opid"] = opid
    return {"opid": opid, "state_code": st["state_code"], "remain_sec": remain}

@app.post("/actuators/{name}/set")
def set_state(name: str, req: SetReq):
    st = ensure(name)
    if req.opid is not None:
        st["opid"] = req.opid
    if req.state_code is not None:
        st["state_code"] = req.state_code
        # READY로 강제 전환 시 타이머 해제
        if req.state_code == READY:
            st["started_ts"] = None
            st["end_ts"] = None
    if req.remain_sec is not None:
        # 남은 시간을 직접 세팅(테스트 목적)
        now = time()
        st["started_ts"] = now
        st["end_ts"] = now + max(0, int(req.remain_sec))
        st["state_code"] = WORKING if req.remain_sec > 0 else READY
    remain = 0
    if st.get("end_ts"):
        remain = max(0, int(st["end_ts"] - time()))
    return {"ok": True, "opid": st["opid"], "state_code": st["state_code"], "remain_sec": remain}
