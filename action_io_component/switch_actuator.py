from utils import pack_i32, unpack_i32
from typing import List, Dict
from actuator_base import Actuator, BaseState, Command
from ksconstants import STATCODE

STATUS = {"state":0, "opid":1, "remain":[2,3]}

class SwitchActuator(Actuator[BaseState]):
    def _encode_command(self, cmd: Command) -> List[int]:
        print(cmd.name.name) # TODO 로그구현
        opid = self._alloc_opid
        print(opid)
        print(cmd.duration_sec)
        if cmd.duration_sec:
            return [cmd.name.value, opid].extend(pack_i32(int(cmd.duration_sec)))
        return [cmd.name.value, opid]
    
    def _decode(self, regs: List[int]) -> BaseState:
        # TODO 로그
        return BaseState(STATCODE(regs[STATUS["state"]]), regs[STATUS["opid"]], unpack_i32(regs[STATUS["remain"][0]],regs[STATUS["remain"][1]]))


