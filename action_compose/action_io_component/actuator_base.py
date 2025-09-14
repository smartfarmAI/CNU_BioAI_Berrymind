from dataclasses import dataclass
from typing import Generic, TypeVar, Protocol, Optional, Dict, Any, List
from ksconstants import STATCODE, CMDCODE
from dataclasses import asdict

# ---- 표준 커맨드/상태 ----
@dataclass
class Command:
    name: CMDCODE               # 'ON', 'OFF', 'OPEN', 'CLOSE', 'JUST_WATER', 'NUT_WATER' 등
    duration_sec: Optional[int]=0


@dataclass
class BaseState: # 장비가 반환하는 스테이트 
    state: STATCODE            # READY = 0, ERROR = 1 등
    opid: int                  # 최근 명령 ID
    remain_sec: int            # 남은 구동시간

@dataclass
class RetractableState(BaseState):
    open_pct: int        # 현재 개폐율 0~100

@dataclass
class NutSupplyState(BaseState):
    alarm: int
    area: int

ST = TypeVar("ST", bound=BaseState)

class Actuator(Generic[ST]):
    """
    공통 베이스: Modbus 접근, 상태 읽기/명령 쓰기 프로토콜을 표준화.
    하위클래스는 register map과 encode/decode만 구현.
    """
    def __init__(self, client, regmap:Dict[str,int]):
        self.client = client
        self.reg = regmap
        self.now_opid = 0
        self._next_opid = 1

    # ---- 하위 클래스가 오버라이드할 것 ----
    def _encode_command(self, cmd: Command) -> List[int]:
        raise NotImplementedError
    def _decode(self, regs: List[int]) -> ST:
        raise NotImplementedError
    def read_sensor(self) -> Dict:
        raise NotImplementedError

    # ---- 공통 I/O ----

    def _read(self, start_addr, cnt) -> List[int]:
        rr = self.client.read_holding_registers(start_addr, count = cnt, device_id=self.reg['device_id'])
        regs = rr.registers if rr else [0] * cnt
        return regs

    def send(self, cmd: Command) -> int:
        print(f"base send 진입 {cmd}")
        payload = self._encode_command(cmd)

        print(f"payload 인코딩 결과 {payload}")
        print(f"cmd_start_addr : {self.reg['cmd_start_addr']} \ndevice_id : {self.reg["device_id"]}")
        # 상태 체크하는건 상태머신에서
        res = self.client.write_registers(self.reg['cmd_start_addr'], payload, device_id=self.reg["device_id"])
        # TODO: 명령 보내고 결과를 받아오는 것 구현
        print(res)
        return self.now_opid
    
    def read_state(self) -> Dict:
        device_id, sa, cnt = self.reg["device_id"], self.reg["state_start_addr"], self.reg["state_cnt"]
        rr = self._read(sa,cnt)
        st = self._decode(rr)
        return asdict(st)

    def _alloc_opid(self) -> int:
        self.now_opid = self._next_opid
        self._next_opid += 1
        if self._next_opid > 20000:
            self._next_opid = 1
        return self.now_opid
