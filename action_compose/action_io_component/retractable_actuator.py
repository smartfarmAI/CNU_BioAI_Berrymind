from typing import List
from utils import pack_i32, unpack_i32
from actuator_base import Actuator, Command, RetractableState
from ksconstants import STATCODE, CMDCODE
import logging
from logger_config import logger

# "시간 지정" 명령 집합
TIMED_COMMANDS = frozenset({CMDCODE.TIMED_OPEN, CMDCODE.TIMED_CLOSE})

# "작업 중" 상태 집합
WORKING_CODES = frozenset({
    STATCODE.WORKING, STATCODE.OPENING, STATCODE.CLOSING,
    STATCODE.PREPARING, STATCODE.SUPPLYING, STATCODE.FINISHING
})

def is_working_code(code: STATCODE) -> bool:
    try:
        return code in WORKING_CODES
    except Exception as e:
        logger.warning(f"상태 코드 확인 오류: {e}")
        return False

def is_CMD_code(cmd_code: CMDCODE) -> bool:
    try:
        return cmd_code in TIMED_COMMANDS
    except Exception as e:
        logger.warning(f"명령 코드 확인 오류: {e}")
        return False

STATUS = {"state":1, "opid":0, "remain":[2,3], "open_pct":4}
CMD    = {"cmd":0, "opid":1, "duration":[2,3], "target_pct":4}

class RetractableActuator(Actuator[RetractableState]):
    
    def __init__(self, state_addr: int, cmd_addr: int):
        super().__init__()
        self.state_addr = state_addr
        self.cmd_addr = cmd_addr

    def _encode_command(self, cmd: Command) -> List[int]:
<<<<<<< HEAD:action_io_component/retractable_actuator.py
<<<<<<< HEAD
        opid = self._alloc_opid
        if is_CMD_code(cmd.name):
            if cmd.duration_sec == 0:
                raise ValueError(f"{cmd.name} 명령은 실행 시간이 필요합니다")
            logger.info(f"{cmd.name} 인코딩: duration={cmd.duration_sec}s")
            regs = [cmd.name.value, opid].extend(pack_i32(int(cmd.duration_sec)))
        else:
            regs = [cmd.name.value, opid]
        logger.debug(f"레지스터 배열: {regs}")
        return regs
=======
=======
        print(f"_encode_command in : cmd {cmd}")
>>>>>>> 862a96638f1cfeff6e6c7e3bb270345c01ad2173:action_compose/action_io_component/retractable_actuator.py
        # TODO 로그 구현
        try:
            opid = self._alloc_opid()
        except Exception:
            print("opid 발급 에러")
        # TODO cmd가 시간열림 혹은 시간 닫힘인데 duration_sec가 0이면 에러
        if cmd.duration_sec:
<<<<<<< HEAD:action_io_component/retractable_actuator.py
            return [cmd.name.value, opid].extend(pack_i32(int(cmd.duration_sec)))
        return [cmd.name.value, opid]
>>>>>>> 6325297f44fa4562f15e5ca6504827e03c45035d

    def _decode(self, regs: List[int]) -> RetractableState:
        # TODO 로그
        state = RetractableState(
                STATCODE(regs[STATUS["state"]]), 
                regs[STATUS["opid"]], 
                unpack_i32(
=======
            print([cmd.name.value, opid, *pack_i32(int(cmd.duration_sec or 0))])
            return [cmd.name.value, opid, *pack_i32(int(cmd.duration_sec or 0))]
        print([cmd.name.value, opid, *pack_i32(int(cmd.duration_sec or 0))])
        return [cmd.name.value, opid, *pack_i32(int(cmd.duration_sec or 0))]

    def _decode(self, regs: List[int]) -> RetractableState:
        # TODO 로그
        return RetractableState(
                state=STATCODE(regs[STATUS["state"]]), 
                opid=regs[STATUS["opid"]], 
                remain_sec=unpack_i32(
>>>>>>> 862a96638f1cfeff6e6c7e3bb270345c01ad2173:action_compose/action_io_component/retractable_actuator.py
                    regs[STATUS["remain"][0]],
                    regs[STATUS["remain"][1]]
                ),
                open_pct=regs[STATUS["open_pct"]]
        )
        if is_working_code(state.state):
            logger.info(f"작업 중: {state.state}, 남은시간={state.remain_sec}s")
        else:
            logger.debug(f"상태: {state.state}")
        return state

    # TODO 좌우천장은 따로 구현 해야함

    def encode(self, cmd: CMDCODE, duration_sec: int = 0) -> List[int]:
        return self._encode_command(Command(cmd, duration_sec))

    def decode(self, regs: List[int]) -> RetractableState:
        return self._decode_state(regs)

class SkyWindowLeft(RetractableActuator):
    def __init__(self):
        super().__init__(state_addr=267, cmd_addr=567)

class SkyWindowRight(RetractableActuator):
    def __init__(self):
        super().__init__(state_addr=272, cmd_addr=572)
