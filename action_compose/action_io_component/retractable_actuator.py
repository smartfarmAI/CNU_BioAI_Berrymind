from typing import List
from utils import pack_i32, unpack_i32
from actuator_base import Actuator, Command, RetractableState
from ksconstants import STATCODE

STATUS = {"state":1, "opid":0, "remain":[2,3], "open_pct":4}
CMD    = {"cmd":0, "opid":1, "duration":[2,3], "target_pct":4}

class RetractableActuator(Actuator[RetractableState]):
    def _encode_command(self, cmd: Command) -> List[int]:
        print("_encode_command in")
        # TODO 로그 구현
        try:
            opid = self._alloc_opid()
        except Exception:
            print("opid 발급 에러")
        # TODO cmd가 시간열림 혹은 시간 닫힘인데 duration_sec가 0이면 에러
        if cmd.duration_sec:
            print([cmd.name.value, opid].extend(pack_i32(int(cmd.duration_sec))))
            return [cmd.name.value, opid].extend(pack_i32(int(cmd.duration_sec)))
        print([cmd.name.value, opid])
        return [cmd.name.value, opid]

    def _decode(self, regs: List[int]) -> RetractableState:
        # TODO 로그
        return RetractableState(
                state=STATCODE(regs[STATUS["state"]]), 
                opid=regs[STATUS["opid"]], 
                remain_sec=unpack_i32(
                    regs[STATUS["remain"][0]],
                    regs[STATUS["remain"][1]]
                ),
                open_pct=regs[STATUS["open_pct"]]
        )

    # TODO 좌우천장은 따로 구현 해야함