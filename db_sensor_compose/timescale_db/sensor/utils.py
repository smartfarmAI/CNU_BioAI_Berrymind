import struct
from typing import Tuple

# ---- pack/unpack helpers ----
def pack_i32(v:int) -> tuple[int,int]: # 실제 레지스터에 쓸때 필요
    return struct.unpack('HH', struct.pack('i', v))
def unpack_i32(h1:int,h2:int) -> int: # 실제 레지스터에 보낼 때 필요
    return struct.unpack('i', struct.pack('HH', h1, h2))[0]

def pack_f32(v:float) -> Tuple[int,int]:
    return struct.unpack('HH', struct.pack('f', v))
def unpack_f32(h1:int,h2:int) -> float:
    return struct.unpack('f', struct.pack('HH', h1, h2))[0]