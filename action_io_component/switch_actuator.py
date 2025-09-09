from utils import pack_i32, unpack_i32
from typing import List, Dict
from actuator_base import Actuator, BaseState, Command
from ksconstants import STATCODE
import logging
from logger_config import logger

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

STATUS = {"state":1, "opid":0, "remain":[2,3]}

class SwitchActuator(Actuator[BaseState]):
    def _encode_command(self, cmd: Command) -> List[int]:
<<<<<<< HEAD
        logger.info(f"명령 이름: {cmd.name.name}")
        opid = self._alloc_opid
        logger.info(f"opid: {opid}, duration_sec: {cmd.duration_sec}")

=======
        print(cmd.name.name) # TODO 로그구현
        opid = self._alloc_opid()
        print(opid)
        print(cmd.duration_sec)
>>>>>>> 6325297f44fa4562f15e5ca6504827e03c45035d
        if cmd.duration_sec:
            return [cmd.name.value, opid].extend(pack_i32(int(cmd.duration_sec)))
        return [cmd.name.value, opid]
    
    def _decode(self, regs: List[int]) -> BaseState:
<<<<<<< HEAD
        
        logger.info(f"레지스터 디코딩: {regs}")
=======
        # TODO 로그
        print(regs)
        return BaseState(state=STATCODE(regs[STATUS["state"]]), opid=regs[0], remain_sec=unpack_i32(regs[STATUS["remain"][0]],regs[STATUS["remain"][1]]))

>>>>>>> 6325297f44fa4562f15e5ca6504827e03c45035d

        return BaseState(
            STATCODE(regs[STATUS["state"]]),
            regs[STATUS["opid"]], 
            unpack_i32(regs[STATUS["remain"][0]],regs[STATUS["remain"][1]]))
