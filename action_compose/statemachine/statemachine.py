import asyncio, time
from typing import Optional, Protocol
from transitions import Machine
from ksconstants import STATCODE, CMDCODE
import requests

# “워킹으로 간주”할 코드 집합(필요시 여기만 바꾸면 됨)
WORKING_CODES = frozenset({
    STATCODE.WORKING, STATCODE.OPENING, STATCODE.CLOSING,
    STATCODE.PREPARING, STATCODE.SUPPLYING, STATCODE.FINISHING
})

def is_working_code(code: STATCODE) -> bool:
    try:
        return code in WORKING_CODES
    except Exception:
        return False

class DeviceFSM:
    states = ["READY", "WORKING", "ERROR"]

    def __init__(self, actuator_name: str, host: str, verify_interval: float = 1.0, timeout = 3000):
        self.actuator_name = actuator_name
        self.host = host.rstrip("/")
        self.base_url = f"{self.host}/actuators/{self.actuator_name}"
        self.timeout = timeout # 이 시간동안 안되면 실패로 간주
        self.machine = Machine(model=self, states=self.states, initial="READY", queued=True)
        self.machine.add_transition("start",  "READY",   "WORKING", after="on_start")
        self.machine.add_transition("finish", "WORKING", "READY",   after="on_finish")
        self.machine.add_transition("fail",   "*",       "ERROR",   after="on_fail")
        self.machine.add_transition("reset",  "ERROR",   "READY")

        self.want_opid: Optional[int] = None
        self.deadline_ts: float = 0.0
        self._verify_interval = verify_interval
        self._task: Optional[asyncio.Task] = None

        # 디버깅용: 마지막 장비 코드/서브상태 저장
        self.last_state_code: Optional[int] = STATCODE["READY"]

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"
    
    def _send_command(self, cmd_name: str, duration_sec: int) -> int:
        print(f"actionio에 요청을 보냅니다. {self.actuator_name} cmd_name : {cmd_name} duration_sec : {duration_sec}")
        r = requests.post(
            self._url("/send_command"),
            json={"cmd_name": cmd_name, "duration_sec": duration_sec},
            timeout=self.timeout,
        )
        print(f"actionio에 요청을 보낸 결과 {self.actuator_name} {r.json()}")
        r.raise_for_status()
        # TODO self.state에 결과 받아서 와야함
        return int(r.json()["opid"])
    
    def _read_state(self):
        r = requests.get(self._url("/get_state"), timeout=self.timeout)
        r.raise_for_status()
        js = r.json()
        return js  # {"opid": ..., "state_code": ...}
    
    # --- 외부 진입점 ---
    async def start_job(self, cmd_name: str, duration_sec: int = 0) -> int:
        # 여기서 한번 상태를 체크 할것.
        
        if self.state != "READY":
            print(f"상태가 READY가 아닙니다. last_opid : {self.last_opid}")
            return self.last_opid
            # raise RuntimeError(f"busy (state={self.state})")
        print(f"{self.actuator_name} 요청을 보냅니다. {cmd_name} {duration_sec}")
        opid = await asyncio.to_thread(self._send_command, cmd_name, duration_sec)
        ttl = self.timeout
        self.start(opid=opid, deadline_ts=time.time() + ttl)
        if not self._task or self._task.done():
            self._task = asyncio.create_task(self._verify_loop())
        return opid
    
    # --- 리셋 ---
    async def reset(self):
        print(f"{self.actuator_name} 리셋 합니다.")
        self.state = "WORKING"
        opid = await asyncio.to_thread(self._send_command, "OFF")
        if not self._task or self._task.done():
            self._task = asyncio.create_task(self._verify_loop())
        print(f"{self.actuator_name} 리셋 완료 {opid}")
        return opid


    # --- 전이 훅 ---
    def on_start(self, opid: int, deadline_ts: float):
        self.want_opid = opid
        self.deadline_ts = deadline_ts
        print(f"{self.actuator_name} {opid} 시작됬습니다.")

    def on_finish(self):
        print(f"{self.actuator_name} {self.want_opid} 끝났습니다.") # TODO: 이름도 같이 나오게
        self.want_opid = None # opid 초기화

    def on_fail(self):
        print(f"{self.actuator_name} {self.want_opid} 에러")
        self.want_opid = None

    # --- 검증 루프 ---
    async def _verify_loop(self):
        """
        WORKING일 때만 주기적으로 read_state().
        성공 조건(예시): opid 반영 && 더 이상 워킹 코드가 아님 → finish()
        실패 조건: TTL 초과 → fail()
        """
        while True:
            await asyncio.sleep(self._verify_interval)
            if not is_working_code(STATCODE[self.state]):
                continue

            if self.want_opid and time.time() > self.deadline_ts:
                print("시간조건으로 인해 fail로 넘어갑니다.")
                self.fail()
                continue

            st = await asyncio.to_thread(self._read_state)
            print(f"state 요청으로 인해 받은 값 {self.actuator_name} {st}")
            opid = st.get("opid",-1) # TODO 에러 구현
            code = st.get("state",STATCODE["ERROR"]) # TODO 에러구현

            self.last_opid = int(opid) if opid is not None else None
            self.last_state_code = int(code) if code is not None else None

            # 1) 에러 코드 즉시 감지
            if self.last_state_code == STATCODE["ERROR"]:
                print(f"에러 코드 즉시 감지로 인해 fail로 넘어갑니다. {self.last_state_code}")
                self.fail()
                continue

            # 2) 우리가 보낸 opid가 장비에 반영됐는지
            print(f"opid 받은것 : {opid}, want_opid : {self.want_opid} last_state_code : {self.last_state_code}")
            reflected = (opid == self.want_opid)

            # 3) 반영되었고, 장비가 더 이상 '워킹 코드'가 아니면 완료로 간주
            #    (장비가 세부코드를 안 주는 환경이면, 아래 조건을 'reflected'만으로도 운용 가능)
            if self.want_opid and reflected and not is_working_code(self.last_state_code):
                self.finish()
                continue

            # 4) 반영만 되었고 아직 워킹 중이면 계속 기다림
            #    (세부코드를 못 받는다면, finish 조건을 'reflected'로 바꾸면 즉시 종료됨)
