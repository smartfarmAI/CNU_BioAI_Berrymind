from dataclasses import dataclass
from typing import Dict, Any
import time
from apscheduler.schedulers.background import BackgroundScheduler
import hashlib
from datetime import datetime, timedelta


@dataclass(frozen=True)
class PlanItem: 
    action_name:str
    action_param:Dict[str,Any]

@dataclass
class Plan: 
    items:Dict[str,PlanItem]
    ts_ms:int # 만들어진 시각

#룰 엔진에서 결정된 액션을 플랜으로 변환하는 함수
def compile_plan(decisions: Dict[str, Any]) -> Plan:
    items = {
        act: PlanItem(d["action_name"], d["action_param"])
        for act, d in decisions.items()
    }
    return Plan(items=items, ts_ms=int(time.time() * 1000))


# 플랜을 안전하게 한번씩 보내는 스케쥴러
class PlanScheduler:
    def __init__(self, dispatch_fn, debounce_sec=0):
        self.sched = BackgroundScheduler(job_defaults={"coalesce": True, "misfire_grace_time": 5, "max_instances": 1})
        self.sched.start()
        self.dispatch_fn = dispatch_fn      # 상태머신에 전달하는 콜백
        self.last_sig = {}                  # 구동기별 마지막 시그니처, 디듀프 기준
        self.debounce = {}                  # 구동기별 디바운스 만료시각 구동기별로 마지막 명령이 유효한 만료시각을 저장. 예) "CO2": 2025-09-02 03:00:10 
        self.debounce_sec = debounce_sec    # 모든 구동기에 공통으로 적용할 디바운스 시간(초)
        self.global_until = datetime.min    # 전역 디바운스 만료시각 
    """
    액션이름+파라미터로 고유 서명
    동일 명령이면 같은 해시 → 디듀프 가능
    """
    def _sig(self, item: PlanItem) -> str:
        key = f"{item.action_name}|{sorted(item.action_param.items())}"
        return hashlib.md5(key.encode()).hexdigest()[:10]
    
    """
    같은 구동기에 같은 시그니처가 윈도우 내면 무시
    통과 시 최신 시그니처/만료시각 갱신
    """
    def submit_plan(self, plan: Plan):
        now = datetime.now()
        
        # 전역 디바운스: 폭주 방지
        if self.debounce_sec > 0 and now < self.global_until:
            return
        
        scheduled_any = False
        
        for act, item in plan.items.items():
            sig = self._sig(item)
            pause = int(item.action_param.get("pause_sec", 0))
            duration = int(item.action_param.get("duration_sec", 0))
            window_sec = max(0, pause + duration)
            if self.last_sig.get(act) == sig and self.debounce.get(act, now) > now:
                print(f"{item.action_param.get('actuator', '')} pause_sec로 인한 디듀프")
                continue
            self.last_sig[act] = sig
            if window_sec > 0:
                self.debounce[act] = now + timedelta(seconds=window_sec)
            # 고정 job_id로 교체 등록
            self.sched.add_job(
                self.dispatch_fn, 
                "date", 
                run_date=now,
                id=f"{act}:apply",
                replace_existing=True,
                args=[act, item]
            )
            scheduled_any = True
        
        # 전역 디바운스 갱신: 이번 제출에서 하나라도 등록되면 활성화
        if scheduled_any and self.debounce_sec > 0:
            self.global_until = now + timedelta(seconds=self.debounce_sec)