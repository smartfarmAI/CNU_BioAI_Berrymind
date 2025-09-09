from typing import List, Dict
from actuator_base import Actuator, Command, NutSupplyState
from ksconstants import STATCODE, CMDCODE
from utils import pack_i32, unpack_f32, unpack_i32
import logging
from logger_config import logger

TIMED_COMMANDS = frozenset({
    CMDCODE.NUT_WATER, CMDCODE.JUST_WATER
})

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

def is_CMD_code(code: CMDCODE) -> bool:
    try:
        return code in TIMED_COMMANDS
    except Exception as e:
        logger.warning(f"명령 코드 확인 오류: {e}")
        return False

STATUS = {"state":0, "area":1, "alarm":2, "opid":3, "remain":[4,5]}
CMD    = {"cmd":0, "opid":1, "start_area":2, "end_area":3, "time":[4,5], "ec":[6,7], "ph":[8,9]}
SENSOR = {
            "ec": {
                "addr":204
            },
            "ph": {
                "addr":213
            },
            "flow": {
                "addr":225
            }
        }

class NutSupplyActuator(Actuator[NutSupplyState]):
    def _encode_command(self, cmd: Command) -> List[int]:
        # TODO 로그 구현
        opid = self._alloc_opid
        # cmd.duration_sec 0 이면 안되는거 검증 코드
        if cmd.duration_sec == 0:
            raise ValueError(f"{cmd.name}명령은 실행 시간이 필요합니다")
        logger.info(f"명령 인코딩 시작: '{cmd.name}', 작업ID={opid}, 실행시간={cmd.duration_sec}초")

        # start_area, end_area는 1로 고정
        return [cmd.name.value, opid, 1, 1].extend(pack_i32(int(cmd.duration_sec)))

    def _decode_state(self, regs: List[int]) -> NutSupplyState:
        state = NutSupplyState(
            state=STATCODE(regs[STATUS["state"]]),
            area=regs[STATUS["area"]],
            alarm=regs[STATUS["alarm"]],
            opid=regs[STATUS["opid"]],
            remain_sec=unpack_i32(regs[STATUS["remain"][0]],regs[STATUS["remain"][1]])
        )
        logger.debug(f"상태 디코딩 완료: 상태={state.state}, 영역={state.area}, 남은시간={state.remain_sec}초")
        return state
    
    def read_sensor(self) -> Dict:
        res = {"ec":0.0,"ph":0.0,"flow":0.0}
        for key in res.keys():
            regs = self._read(SENSOR[key]["addr"],3)
            res[key] = unpack_f32(regs[0],regs[1])
            logger.debug(f"센서 '{key}' 값: {res[key]}")
        logger.info(f"전체 센서 측정값: EC={res['ec']}, pH={res['ph']}, 유량={res['flow']}")
        return res
