import asyncio, time
from typing import Optional, Protocol, Any
from transitions import Machine
from ksconstants import STATCODE, CMDCODE
import requests

# “워킹으로 간주”할 코드 집합(필요시 여기만 바꾸면 됨)
WORKING_CODES = frozenset({
    STATCODE.OPENING, STATCODE.CLOSING,
    STATCODE.PREPARING, STATCODE.SUPPLYING, STATCODE.FINISHING
})

OPEN_CODES = frozenset({CMDCODE.OPEN,CMDCODE.TIMED_OPEN})
CLOSE_CODES = frozenset({CMDCODE.CLOSE,CMDCODE.TIMED_CLOSE})

def is_working_code(code: STATCODE) -> bool:
    try:
        return code in WORKING_CODES
    except Exception:
        return False

def is_open_code(code: STATCODE) -> bool:
    try:
        return code in OPEN_CODES
    except Exception:
        return False

def is_close_code(code: STATCODE) -> bool:
    try:
        return code in CLOSE_CODES
    except Exception:
        return False

class DeviceFSM:

    def __init__(self, actuator_name: str, host: str, verify_interval: float = 1.0, timeout = 3000):
        self.actuator_name = actuator_name
        self.host = host.rstrip("/")
        self.base_url = f"{self.host}/actuators/{self.actuator_name}"
        self.timeout = timeout # 이 시간동안 안되면 실패로 간주
        self.state = 0
        self.last_state_code = 0
        self.last_open_pct = None

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"
    
    def _send_command(self, payload: dict[str, Any]) -> int:
        print(f"actionio에 요청을 보낼준비 {self.actuator_name} cmd_name : {payload}")
        
        if self.last_state_code != 0:
            print(f"현재 READY 상태가 아니여서 actionio에 요청을 보내지 않습니다. {self.actuator_name} last_state_code : {self.last_state_code} cmd_name : {payload['cmd_name']}")
            return -1
        elif CMDCODE[payload["cmd_name"]] == STATCODE(self.last_state_code):
            print(f"요청값과 현재 상태가 같아 actionio에 요청을 보내지 않습니다. {self.actuator_name} last_state_code : {self.last_state_code} cmd_name : {payload['cmd_name']}")
            return -1
        elif is_open_code(CMDCODE[payload["cmd_name"]]) and self.last_open_pct == 100:
            print(f"{self.actuator_name}이 다 열려있어서 actionio에 요청을 보내지 않습니다.  last_state_code : {self.last_state_code}")
            return -1
        elif is_close_code(CMDCODE[payload["cmd_name"]]) and self.last_open_pct == 0:
            print(f"{self.actuator_name}이 다 닫혀있어서 actionio에 요청을 보내지 않습니다.  last_state_code : {self.last_state_code}")
            return -1
        
        r = requests.post(
            self._url("/send_command"),
            json=payload,
            timeout=self.timeout,
        )
        print(f"actionio에 요청을 보낸 결과 {self.actuator_name} {r.json()}")
        r.raise_for_status()
        
        return int(r.json()["opid"])
    
    def _read_state(self):
        r = requests.get(self._url("/get_state"), timeout=self.timeout)
        r.raise_for_status()
        js = r.json()
        return js  # {"opid": ..., "state": ...}
    
    # --- 외부 진입점 ---
    async def start_job(self, payload: dict[str, Any]) -> int:
        st = await asyncio.to_thread(self._read_state)
        opid = st.get("opid",-1) # TODO 에러 구현
        code = st.get("state",STATCODE["ERROR"])
        self.last_state_code = int(code) if code is not None else None
        open_pct = st.get("open_pct",-1) 
        self.last_open_pct = int(open_pct)

        opid = await asyncio.to_thread(self._send_command, payload)
        return opid
