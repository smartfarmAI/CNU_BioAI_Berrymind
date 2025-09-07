import asyncio, time
from typing import Optional
import requests

class STATCODE:
    READY = 100
    ERROR = 900
    WORKING = 201

def is_working_code(code: Optional[int]) -> bool:
    return code in {STATCODE.WORKING}

def _extract_remaining(js: dict):
    # 다양한 키를 남은시간(초)로 정규화
    for k in ("remaining_sec", "remain_sec", "remain"):
        if k in js and js[k] is not None:
            try:
                return int(js[k])
            except Exception:
                pass
    return None

class DeviceFSM:
    states = ["READY", "WORKING", "ERROR"]

    def __init__(self, actuator_name: str, host: str, verify_interval: float = 1.0, timeout: float = 30.0):
        self.actuator_name = actuator_name
        self.host = host.rstrip("/")
        self.base_url = f"{self.host}/actuators/{self.actuator_name}"
        self.timeout = timeout
        self.state = "READY"
        self.want_opid: Optional[int] = None
        self.deadline_ts: float = 0.0
        self._verify_interval = verify_interval
        self._task: Optional[asyncio.Task] = None

        # 캐시
        self.last_state_code: Optional[int] = STATCODE.READY
        self.last_opid: Optional[int] = None
        self.last_remaining_sec: Optional[int] = None

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _send_command(self, cmd_name: str, duration_sec: int) -> int:
        r = requests.post(
            self._url("/send_command"),
            json={"cmd_name": cmd_name, "duration_sec": duration_sec},
            timeout=self.timeout,
        )
        r.raise_for_status()
        js = r.json()
        opid = int(js.get("opid"))
        self.last_opid = opid
        # Action IO가 돌려주는 상태/남은 시간 즉시 반영
        if js.get("state_code") is not None:
            self.last_state_code = int(js["state_code"])
        rem = _extract_remaining(js)
        if rem is not None:
            self.last_remaining_sec = rem
        return opid

    def _read_state(self):
        r = requests.get(self._url("/get_state"), timeout=self.timeout)
        r.raise_for_status()
        js = r.json()  # {"opid": ..., "state_code": ..., "remain_sec"/"remaining_sec"/"remain": ...}
        return js

    async def start_job(self, cmd_name: str, duration_sec: int = 0) -> int:
        # Preflight: 실제 IO가 READY가 아니면 명령을 보내지 않음 (외부 셧다운/점유 고려)
        try:
            js = await asyncio.to_thread(self._read_state)
            code = js.get("state_code", None)
            if code is not None and int(code) != STATCODE.READY:
                self.last_state_code = int(code)
                rem = _extract_remaining(js)
                if rem is not None:
                    self.last_remaining_sec = rem
                raise RuntimeError("preflight_not_ready")
        except Exception:
            # 읽기 실패도 안전 쪽으로 보수적으로 차단
            raise RuntimeError("preflight_read_failed")

        if self.state != "READY":
            raise RuntimeError(f"busy (state={self.state})")
        opid = await asyncio.to_thread(self._send_command, cmd_name, duration_sec)
        self.want_opid = opid
        self.state = "WORKING"
        # TTL은 안전망: 남은시간이 있으면 그 +5초를 최소로 보장
        ttl = max(self.timeout, (self.last_remaining_sec or 0) + 5)
        self.deadline_ts = time.time() + ttl
        if not self._task or self._task.done():
            self._task = asyncio.create_task(self._verify_loop())
        return opid

    def on_start(self, opid: int, deadline_ts: float):
        pass

    def on_finish(self):
        self.want_opid = None

    def on_fail(self):
        self.want_opid = None

    async def _verify_loop(self):
        while True:
            await asyncio.sleep(self._verify_interval)

            # TTL 초과 처리
            if self.want_opid and time.time() > self.deadline_ts:
                self.state = "ERROR"
                self.on_fail()
                return

            try:
                st = await asyncio.to_thread(self._read_state)
            except Exception:
                continue

            opid = st.get("opid", None)
            code = st.get("state_code", None)
            rem = _extract_remaining(st)

            if opid is not None: self.last_opid = int(opid)
            if code is not None: self.last_state_code = int(code)
            if rem is not None: self.last_remaining_sec = rem

            # 외부 시스템 영향 포함: IO 상태를 신뢰하여 전이
            if self.last_state_code == STATCODE.ERROR:
                self.state = "ERROR"
                self.on_fail()
                return
            if self.want_opid and self.last_state_code == STATCODE.READY:
                self.state = "READY"
                self.on_finish()
                return
