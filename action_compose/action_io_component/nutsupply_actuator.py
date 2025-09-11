from typing import List, Dict
from actuator_base import Actuator, Command, NutSupplyState
from ksconstants import STATCODE
from utils import pack_i32, unpack_f32, unpack_i32

STATUS = {"state":0, "area":1, "alarm":2, "opid":3, "remain":[4,5]}
CMD    = {"cmd":0, "opid":1, "start_area":2, "end_area":3, "time":[4,5], "ec":[6,7], "ph":[8,9]}
# SENSOR = {
#             "ec": {
#                 "addr":204
#             },
#             "ph": {
#                 "addr":213
#             },
#             "flow": {
#                 "addr":225
#             }
#         }

class NutSupplyActuator(Actuator[NutSupplyState]):
    def _encode_command(self, cmd: Command) -> List[int]:
        # TODO 로그 구현
        opid = self._alloc_opid()
        # cmd.duration_sec 0 이면 안되는거 검증 코드
        # start_area, end_area는 1로 고정
        return [cmd.name.value, opid, 1, 1, *pack_i32(int(cmd.duration_sec or 0))]

    def _decode_state(self, regs: List[int]) -> NutSupplyState:
        return NutSupplyState(
            state=STATCODE(regs[STATUS["state"]]),
            area=regs[STATUS["area"]],
            alarm=regs[STATUS["alarm"]],
            opid=regs[STATUS["opid"]],
            remain_sec=unpack_i32(regs[STATUS["remain"][0]],regs[STATUS["remain"][1]])
        )
    
    # def read_sensor(self) -> Dict:
    #     res = {"ec":0.0,"ph":0.0,"flow":0.0}
    #     for key in res.keys():
    #         regs = self._read(SENSOR[key]["addr"],3)
    #         res[key] = unpack_f32(regs[0],regs[1])
    #     return res

