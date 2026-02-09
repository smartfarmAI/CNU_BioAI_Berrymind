from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, date
from pathlib import Path
from typing import Dict


STATE_PATH = Path("./state_first_photo_date.json")
STATE_PATH.parent.mkdir(parents=True, exist_ok=True)


def _load_state() -> Dict[str, str]:
    """
    { entity_id: "YYYY-MM-DD" }
    """
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {}


def _atomic_save_state(state: Dict[str, str]) -> None:

    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    tmp.replace(STATE_PATH)


# Utils
def _parse_date(date_str: str) -> date:
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def _get_transplant_to_bud_days() -> int:
    
    raw = os.getenv("TRANSPLANT_TO_BUD_DAYS", "10") #숫자로 DAT 분류
    try:
        n = int(raw)
    except ValueError:
        raise ValueError(
            f"Invalid TRANSPLANT_TO_BUD_DAYS={raw}. Must be an integer."
        )
    if n < 0:
        raise ValueError(
            f"Invalid TRANSPLANT_TO_BUD_DAYS={raw}. Must be >= 0."
        )
    return n



# Result schema
@dataclass
class Stage12Result:
    stage: str                 # "S1" or "S2"
    first_photo_date: str      # 기준일(정식일)
    days_since_first: int
    threshold_days: int        # TRANSPLANT_TO_BUD_DAYS 값



# Main decider
class Stage12Decider:
    
    def __init__(self):
        self.state = _load_state()

    def decide(self, entity_id: str, obs_date_str: str) -> Stage12Result:
        obs_date = _parse_date(obs_date_str)
        threshold = _get_transplant_to_bud_days()

        # 기준일 갱신
        if entity_id not in self.state:
            self.state[entity_id] = obs_date.isoformat()
            _atomic_save_state(self.state)
        else:
            stored = _parse_date(self.state[entity_id])
            if obs_date < stored:
                self.state[entity_id] = obs_date.isoformat()
                _atomic_save_state(self.state)

        first_date = _parse_date(self.state[entity_id])
        delta_days = (obs_date - first_date).days

        # S1/S2 결정
        stage = "S2" if delta_days >= threshold else "S1"

        return Stage12Result(
            stage=stage,
            first_photo_date=first_date.isoformat(),
            days_since_first=delta_days,
            threshold_days=threshold,
        )
