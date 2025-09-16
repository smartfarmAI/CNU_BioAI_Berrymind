from typing import List, Dict
from actuator_base import Actuator, NutSupplyCommand, NutSupplyState
from ksconstants import STATCODE
from utils import pack_i32, unpack_f32, unpack_i32, pack_f32

STATUS = {"state":0, "area":1, "alarm":2, "opid":3, "remain":[4,5]}
CMD    = {"cmd":0, "opid":1, "start_area":2, "end_area":3, "time":[4,5], "ec":[6,7], "ph":[8,9]}


class NutSupplyActuator(Actuator[NutSupplyState]):
    def _encode_command(self, cmd: NutSupplyCommand) -> List[int]:
        opid = self._alloc_opid()
        # start_area, end_area는 1로 고정
        if cmd.ec and cmd.ph:
            return [cmd.name.value, opid, 1, 1, 
                    *pack_i32(int(cmd.duration_sec or 0)), 
                    *pack_f32(cmd.ec),
                    *pack_f32(cmd.ph)
                    ]
        return [cmd.name.value, opid, 1, 1, *pack_i32(int(cmd.duration_sec or 0))]

    def _decode(self, regs: List[int]) -> NutSupplyState:
        return NutSupplyState(
            state=STATCODE(regs[STATUS["state"]]),
            area=regs[STATUS["area"]],
            alarm=regs[STATUS["alarm"]],
            opid=regs[STATUS["opid"]],
            remain_sec=unpack_i32(regs[STATUS["remain"][0]],regs[STATUS["remain"][1]])
        )

