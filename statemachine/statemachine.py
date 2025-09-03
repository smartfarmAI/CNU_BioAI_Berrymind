from transitions import Machine

class Actuator:
    states = ["READY", "WORKING", "ERROR"]
    transitions = [
        {"trigger": "request_on", "source": "READY", "dest": "WORKING", "after": "do_on"},
        {"trigger": "end_run",    "source": "WORKING", "dest": "READY", "after": "do_off"},
        {"trigger": "fail",       "source": "*", "dest": "ERROR"},
        {"trigger": "reset",      "source": "ERROR", "dest": "READY"},
    ]

    def __init__(self):
        self.machine = Machine(model=self, states=self.states,
                               transitions=self.transitions, initial="READY")

    # 상태머신에서 IO 호출하는 부분
    def do_on(self, duration=5):
        pass

    def do_off(self):
        pass