import asyncio
from ksconstants import CMDCODE
from statemachine import DeviceFSM

HOST = "http://localhost:8000"
ACTUATOR_NAME = "fcu"

async def main():
    fsm = DeviceFSM(host=HOST, actuator_name=ACTUATOR_NAME, verify_interval=5.0)
    opid = await fsm.start_job(cmd_name="OPEN")
    print("opid:", opid)

    # ↓↓↓ 추가: 상태 바뀔 때마다 한 줄 로그
    prev = fsm.state
    while True:
        if fsm.state != prev:
            print(f"[FSM] {prev} -> {fsm.state}")
            prev = fsm.state
        await asyncio.sleep(5)  # 폴링 간격

if __name__ == "__main__":
    asyncio.run(main())