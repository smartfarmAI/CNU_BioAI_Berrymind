from utils import pack_i32, unpack_i32
from typing import List, Dict
from actuator_base import Actuator, BaseState, Command
from ksconstants import STATCODE
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

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

STATUS = {"state":0, "opid":1, "remain":[2,3]}

class SwitchActuator(Actuator[BaseState]):
    def _encode_command(self, cmd: Command) -> List[int]:
        logger.info(f"명령 이름: {cmd.name.name}")
        opid = self._alloc_opid
        logger.info(f"opid: {opid}, duration_sec: {cmd.duration_sec}")

        if cmd.duration_sec:
            return [cmd.name.value, opid].extend(pack_i32(int(cmd.duration_sec)))
        return [cmd.name.value, opid]
    
    def _decode(self, regs: List[int]) -> BaseState:
        
        logger.info(f"레지스터 디코딩: {regs}")

        return BaseState(
            STATCODE(regs[STATUS["state"]]),
            regs[STATUS["opid"]], 
            unpack_i32(regs[STATUS["remain"][0]],regs[STATUS["remain"][1]]))
