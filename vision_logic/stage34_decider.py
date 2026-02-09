from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Literal, Optional, TypedDict

STATE_PATH = Path("./state_stage34.json")
STATE_PATH.parent.mkdir(parents=True, exist_ok=True)

Stage = Literal["S3", "S4"]
Route = Literal["stage34", "stage12"]


class StageState(TypedDict):
    stage: Stage
    stage_since: str  


def _load_state() -> Dict[str, StageState]:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {}


def _atomic_save_state(state: Dict[str, StageState]) -> None:
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(STATE_PATH)


def _parse_date(date_str: str) -> date:
    return datetime.strptime(date_str, "%Y-%m-%d").date()

def _flag(record, key: str) -> int:
    det = record.get("detections", {}) or {}
    return 1 if int(det.get(key, 0)) == 1 else 0


@dataclass
class Stage34Result:
    stage: Optional[Stage]          # 최종 stage (없으면 None)
    prev_stage: Optional[Stage]     # 이전 stage
    prev_since: Optional[str]       # 이전 stage_since
    reason: str
    route_to: Route                 # "stage34" or "stage12"


class Stage34Decider:

    def __init__(self):
        self.state: Dict[str, StageState] = _load_state()

    def decide(self, entity_id: str, record: dict) -> Stage34Result:
        if "date" not in record:
            raise ValueError("record missing 'date' (YYYY-MM-DD)")

        obs_date_str = record["date"]
        obs_date = _parse_date(obs_date_str)

        prev = self.state.get(entity_id)
        prev_stage: Optional[Stage] = prev["stage"] if prev else None
        prev_since: Optional[str] = prev["stage_since"] if prev else None

        flower = _flag(record, "FLOWER")
        green  = _flag(record, "GREEN FRUIT")
        red    = _flag(record, "RED FRUIT")

        # STA
        if (flower + green + red) == 0:
            if prev_stage is None:
                # 꽃, 과실 없는것 stage12로 보내기
                return Stage34Result(
                    stage=None,
                    prev_stage=None,
                    prev_since=None,
                    reason="no evidence; route to stage12",
                    route_to="stage12",
                )
            # satge34 기록이 있으면 유지
            return Stage34Result(
                stage=prev_stage,
                prev_stage=prev_stage,
                prev_since=prev_since,
                reason="no evidence; keep previous stage (likely missing detection)",
                route_to="stage34",
            )

        # 대전제 S4이후 유지
        if prev_stage == "S4" and prev_since is not None:
            since_date = _parse_date(prev_since)
            if obs_date >= since_date:
                return Stage34Result(
                    stage="S4",
                    prev_stage="S4",
                    prev_since=prev_since,
                    reason=f"premise: obs_date({obs_date_str}) >= S4_since({prev_since})",
                    route_to="stage34",
                )

        # 2) S4 판정
        if red == 1:
            self.state[entity_id] = {"stage": "S4", "stage_since": obs_date_str}
            _atomic_save_state(self.state)
            return Stage34Result(
                stage="S4",
                prev_stage=prev_stage,
                prev_since=prev_since,
                reason="rule: red_fruit=1 -> S4",
                route_to="stage34",
            )

        # 3) S3 판정
        if (flower == 1) or (green == 1):
            self.state[entity_id] = {"stage": "S3", "stage_since": obs_date_str}
            _atomic_save_state(self.state)
            return Stage34Result(
                stage="S3",
                prev_stage=prev_stage,
                prev_since=prev_since,
                reason="rule: red=0 and (flower=1 or green=1) -> S3",
                route_to="stage34",
            )

        # 논리상 여기로 올 일 없음(위에서 0,0,0 처리했고 red/flower/green 조건 처리함)
        return Stage34Result(
            stage=None,
            prev_stage=prev_stage,
            prev_since=prev_since,
            reason="unreachable state (check input keys)",
            route_to="stage34",
        )
