# scheduler_component.py
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Dict, Any, Optional, List, DefaultDict, Tuple
from collections import defaultdict, deque
from apscheduler.schedulers.background import BackgroundScheduler

# 타입 별칭
SensorProvider = Callable[[], Dict[str, Any]]           # 센서 스냅샷 dict 반환
ActuatorCommand = Callable[[str, str], None]            # (actuator, "ON"/"OFF")

@dataclass
class Plan:
    actuator: str
    time_band: int
    run_sec: int
    pause_sec: int
    continue_if: Dict[str, Any]   # 예: {"var":"avg_indoor_temp","op":">=","value":28}
    stop_if: Dict[str, Any]       # 예: {"var":"avg_indoor_temp","op":"<","value":28}
    name: str = ""                # 룰 이름(로그용)
    max_cycles: Optional[int] = None  # None이면 무한 반복

class RuleScheduler:
    """
    룰이 내려준 실행계획(Plan)을 받아 단계별로 스케줄링:
      RUN(run_sec ON) → PAUSE(pause_sec OFF) → CHECK(조건평가) → 반복/종료
    - time_band 변경 시 즉시 중지
    - actuator별 이력(history)과 반복 횟수(cycles) 기록
    - 현재 예약된 잡 조회(list_jobs) 제공
    """
    def __init__(self, sensor_provider: SensorProvider, send_cmd: ActuatorCommand):
        self.sched = BackgroundScheduler()
        self.sensor_provider = sensor_provider
        self.send_cmd = send_cmd
        self.jobs: Dict[str, Dict[str, Any]] = {}                 # actuator -> {"plan":Plan, "phase":str}
        self.history: DefaultDict[str, deque[str]] = defaultdict(lambda: deque(maxlen=200))
        self.cycles: DefaultDict[str, int] = defaultdict(int)

    # ---------- 외부 API ----------
    def start(self) -> None:
        if not self.sched.running:
            self.sched.start()

    def shutdown(self) -> None:
        if self.sched.running:
            self.sched.shutdown(wait=False)
        self.jobs.clear()
        self.history.clear()
        self.cycles.clear()

    def submit(self, plan: Plan) -> None:
        """동일 actuator 기존 작업 취소 후 새 플랜 시작(RUN부터)."""
        self.cancel(plan.actuator)
        self.jobs[plan.actuator] = {"plan": plan, "phase": "RUN"}
        self._log(plan.actuator, f"SUBMIT plan='{plan.name}' tb={plan.time_band}")
        self._schedule_in(plan.actuator, seconds=0, phase="RUN")

    def cancel(self, actuator: str) -> None:
        """해당 actuator의 예약 작업 및 상태 초기화."""
        for j in list(self.sched.get_jobs()):
            if j.id.startswith(f"{actuator}-"):
                self.sched.remove_job(j.id)
        if actuator in self.jobs:
            self._log(actuator, "CANCEL all scheduled")
        self.jobs.pop(actuator, None)
        self.cycles.pop(actuator, None)

    def list_jobs(self) -> List[Dict[str, Any]]:
        """현재 예약된 잡 목록."""
        out = []
        for j in self.sched.get_jobs():
            out.append({
                "id": j.id,
                "next_run_time": j.next_run_time,
                "trigger": str(j.trigger),
            })
        return out

    def get_history(self, actuator: str, last: int | None = None) -> List[str]:
        """actuator별 최근 로그 조회."""
        h = list(self.history.get(actuator, []))
        return h[-last:] if last else h

    # ---------- 내부 구현 ----------
    def _schedule_in(self, actuator: str, seconds: int, phase: str) -> None:
        run_at = datetime.now() + timedelta(seconds=seconds)
        job_id = f"{actuator}-{phase}-{int(run_at.timestamp())}"
        self.sched.add_job(
            self._step, "date", id=job_id, run_date=run_at,
            kwargs={"actuator": actuator, "phase": phase}
        )
        self._log(actuator, f"SCHEDULE {phase} in {seconds}s (job_id={job_id})")

    def _step(self, actuator: str, phase: str) -> None:
        state = self.jobs.get(actuator)
        if not state:
            return
        plan: Plan = state["plan"]

        sensor = self.sensor_provider()
        if int(sensor.get("time_band", -1)) != int(plan.time_band):
            self._log(actuator, f"TIMEBAND CHANGED ({sensor.get('time_band')} != {plan.time_band}) → OFF & CANCEL")
            self.send_cmd(actuator, "OFF")
            self.cancel(actuator)
            return

        def _eval(cond: Dict[str, Any], s: Dict[str, Any]) -> bool:
            try:
                v = float(s.get(cond["var"], float("nan")))
                t = float(cond["value"])
            except (TypeError, ValueError):
                return False
            op = cond.get("op")
            return ((op == ">=" and v >= t) or
                    (op == "<=" and v <= t) or
                    (op == ">"  and v >  t) or
                    (op == "<"  and v <  t) or
                    (op == "==" and v == t) or
                    (op == "!=" and v != t))

        if phase == "RUN":
            self._log(actuator, f"RUN {plan.run_sec}s → ON (rule='{plan.name}')")
            self.send_cmd(actuator, "ON")
            state["phase"] = "PAUSE"
            self._schedule_in(actuator, plan.run_sec, "PAUSE")

        elif phase == "PAUSE":
            self._log(actuator, f"PAUSE {plan.pause_sec}s → OFF")
            self.send_cmd(actuator, "OFF")
            state["phase"] = "CHECK"
            self._schedule_in(actuator, plan.pause_sec, "CHECK")

        elif phase == "CHECK":
            if _eval(plan.stop_if, sensor):
                self._log(actuator, f"CHECK STOP_IF met → OFF & CANCEL (sensor={sensor})")
                self.send_cmd(actuator, "OFF")
                self.cancel(actuator)
                return
            if not _eval(plan.continue_if, sensor):
                self._log(actuator, f"CHECK CONTINUE_IF not met → OFF & CANCEL (sensor={sensor})")
                self.send_cmd(actuator, "OFF")
                self.cancel(actuator)
                return

            # 반복 승인
            self.cycles[actuator] += 1
            self._log(actuator, f"CHECK CONTINUE → cycle={self.cycles[actuator]}")
            if plan.max_cycles and self.cycles[actuator] >= plan.max_cycles:
                self._log(actuator, f"MAX_CYCLES reached ({plan.max_cycles}) → OFF & CANCEL")
                self.send_cmd(actuator, "OFF")
                self.cancel(actuator)
                return

            state["phase"] = "RUN"
            self._schedule_in(actuator, 0, "RUN")

    def _log(self, actuator: str, msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self.history[actuator].append(f"[{ts}] {msg}")
