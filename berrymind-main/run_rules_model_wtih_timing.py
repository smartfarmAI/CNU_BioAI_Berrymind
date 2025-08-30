#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rules-only ON/OFF executor (+ timing FSM: delay/min-hold; SR/SS placeholders)

- Reads X data (CSV: train_x.csv or test_X.csv)
- Parses '인공지능 모델.xlsx' (band × actuator, rule/premise)  # 없으면 경고만 출력하고 계속
- Computes timeband (hour fallback; SR/SS placeholders left as TODO)
- Evaluates rules per row to get desired ON/OFF
- Applies per-actuator/per-rule timing (delay_on/off, min_on/off) via FSM
- Writes:
    1) decisions CSV  (timestamp, band_code, <ACT>, <ACT>_reason, ...)
    2) transition log (state-change lines only)

Usage:
  python run_rules_model_with_timing.py \
    --x ./data/train_x.csv \
    --out ./out/decisions.csv \
    --log ./out/transitions.log \
    --actuators_json ./actuators.json \
    --default_delay_on_sec 0 --default_delay_off_sec 0 \
    --default_min_on_sec 0   --default_min_off_sec 0

Rule text timing examples (KOR/ENG both):
  - "지연 30초 후 동작" / "delay 30s ON" → delay_on_sec=30
  - "지연 1분 후 정지" / "delay 60s OFF" → delay_off_sec=60
  - "최소 ON 유지 120초" / "min on 120s"  → min_on_sec=120
  - "최소 OFF 유지 45초" / "min off 45s"  → min_off_sec=45
  - "지연 20초" (ambiguous) → both delay_on_sec=delay_off_sec=20
"""
import argparse, re, json, os, sys
from pathlib import Path
from dataclasses import dataclass
import numpy as np
import pandas as pd

# ---- Default paths (relative to current working dir) ----
EXCEL_RULES_DEFAULT = Path("./인공지능 모델.xlsx")
COLUMN_MAP_DEFAULT  = Path("./column_mapping.json")

# Actuator order for outputs (필요하면 시트에 맞춰 수정)
ACTUATORS = ["FCU","FOG","CO2","유동팬","상부차광스크린","상부보온커텐","좌우천창","양액기"]

# -----------------------------------------------------
# Helpers
# -----------------------------------------------------
def load_column_mapping(p: Path|None):
    if not p or not p.exists():
        return {}
    try:
        j = json.loads(p.read_text(encoding="utf-8"))
        return j.get("mapping", {})
    except Exception:
        return {}

def unify_timestamp(df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    out = df.copy()
    # direct
    for cand in ["timestamp","time","Time","저장시간"]:
        if cand in out.columns:
            out = out.rename(columns={cand:"timestamp"})
            break
    # mapping fallback (src -> 'timestamp')
    if "timestamp" not in out.columns:
        for src, dst in (mapping or {}).items():
            if dst == "timestamp" and src in out.columns:
                out = out.rename(columns={src:"timestamp"})
                break
    if "timestamp" in out.columns:
        out["timestamp"] = pd.to_datetime(out["timestamp"], errors="coerce")
    else:
        out["timestamp"] = pd.NaT
        print("[WARN] 'timestamp' 열을 찾지 못했습니다. 밴드 계산이 부정확할 수 있습니다.")
    return out

def hour_to_band(h):
    if pd.isna(h): return np.nan
    h = int(h)
    if 6 <= h < 9:   return 1  # t1
    if 9 <= h < 12:  return 2  # t2
    if 12 <= h < 15: return 3  # t3
    if 15 <= h < 18: return 4  # t4
    if 18 <= h < 21: return 5  # t5
    if 21 <= h < 24: return 6  # t6
    if 0 <= h < 3:   return 7  # t7
    return 8                    # t8

def add_timebands(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    t = pd.to_datetime(out["timestamp"], errors="coerce")

    # ---- SR/SS TODO placeholders (later: lat/lon/tz-based) ----
    out["SR_time"] = pd.NaT  # TODO
    out["SS_time"] = pd.NaT  # TODO

    # Hour-based fallback 8-band
    out["hour"] = t.dt.hour
    out["band_id"] = out["hour"].map(hour_to_band).astype("Int64")
    out["band_code"] = out["band_id"].map({1:"t1",2:"t2",3:"t3",4:"t4",5:"t5",6:"t6",7:"t7",8:"t8"})
    return out

def parse_excel_rules(xlsx_path: Path) -> pd.DataFrame:
    """엑셀에서 (rule, 대전제) 페어를 찾아 밴드×액추에이터 텍스트를 추출.
       파일이 없거나 파싱 실패 시, 빈 DataFrame 반환."""
    if not xlsx_path.exists():
        print(f"[WARN] 룰 엑셀을 찾지 못했습니다: {xlsx_path}  → 룰 없이 진행합니다.")
        return pd.DataFrame(columns=["band","interval","actuator","rule","premise"])
    try:
        df = pd.read_excel(xlsx_path, sheet_name=0)
    except Exception as e:
        print(f"[WARN] 룰 엑셀을 읽는 중 오류: {e}  → 룰 없이 진행합니다.")
        return pd.DataFrame(columns=["band","interval","actuator","rule","premise"])

    # detect (rule, 대전제) pairs in the first row
    row0 = df.iloc[0].astype(str).str.strip()
    pairs = []
    for j in range(len(df.columns)-1):
        if row0.iloc[j].lower()=="rule" and row0.iloc[j+1]=="대전제":
            pairs.append((j, j+1, df.columns[j], df.columns[j+1]))

    # find band rows (t1..t8)
    bands = df[df.iloc[:,0].astype(str).str.match(r"^t\d+$", na=False)].index.tolist()

    # heuristic: split premise-like lines from rule text (if premise cell is blank)
    premise_keywords = ["대전제","전제","게이트","환기","일사","습도","이슬","금지","중지"]
    ineq = re.compile(r"[<>]=?|≥|≤")
    def split_rule_and_prem(text):
        if not isinstance(text,str): return "",""
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()!=""]
        rule_lines, prem_lines = [], []
        for ln in lines:
            if any(k in ln for k in premise_keywords) or (ineq.search(ln) and ("동작" not in ln and "초" not in ln and "분" not in ln)):
                prem_lines.append(ln)
            else:
                rule_lines.append(ln)
        return "\n".join(rule_lines), "\n".join(prem_lines)

    recs = []
    for idx in bands:
        band = str(df.iloc[idx,0]).strip()
        interval = str(df.iloc[idx,1]).strip()
        for j_rule, j_prem, rc, pc in pairs:
            rule_val = df.iloc[idx, j_rule]
            prem_val = df.iloc[idx, j_prem]
            rule_text = "" if pd.isna(rule_val) else str(rule_val).strip()
            prem_text = "" if pd.isna(prem_val) else str(prem_val).strip()
            if prem_text=="" and rule_text!="":
                r2,p2 = split_rule_and_prem(rule_text)
                if p2.strip()!="":
                    rule_text, prem_text = r2, p2
            recs.append({"band": band, "interval": interval, "actuator": rc,
                         "rule": rule_text, "premise": prem_text})
    return pd.DataFrame(recs)

# ----------- Minimal Korean rule interpreter -----------
# (기존 수치 조건 평가 + 지연/유지시간 파서 추가)

def resolve_signal(row, mapping, keys):
    """row에서 keys(논리명) 또는 매핑된 원본 컬럼을 찾아 값 반환."""
    for k in keys:
        if k in row.index:
            return row[k]
        for src, dst in (mapping or {}).items():
            if dst == k and src in row.index:
                return row[src]
    return np.nan


def _to_num(x):
    try:
        return float(x)
    except Exception:
        return np.nan


def eval_condition_numeric(row, mapping, text):
    """
    Supports:
      - 'co2 300ppm 이하/이상/미만/초과'
      - '온도 28(℃) 이상/이하/미만'
      - '습도 85% 이상/이하/미만'
    Returns: (bool or None, reason)
    """
    txt = str(text)

    # CO2
    m = re.search(r"(\d+(?:\.\d+)?)\s*ppm\s*(이하|이상|이하면|미만|초과)?", txt)
    if m:
        th = float(m.group(1)); op = m.group(2) or "이하"
        val = resolve_signal(row, mapping, ["co2_concentration_1","co2","co2_ppm"])
        val = _to_num(val)
        if pd.isna(val): return None, "co2 missing"
        if op in ("이하","이하면"): return bool(val <= th), f"co2 {val:.1f} ≤ {th}"
        if op in ("이상","초과"):   return bool(val >= th), f"co2 {val:.1f} ≥ {th}"
        if op == "미만":           return bool(val <  th), f"co2 {val:.1f} < {th}"

    # Temperature
    m = re.search(r"온도[^\d]*(\d+(?:\.\d+)?)\s*(?:도|℃)?\s*(이상|이하면|이하|미만|초과)?", txt)
    if m:
        th = float(m.group(1)); op = m.group(2) or "이상"
        val = resolve_signal(row, mapping, ["avg_indoor_temp","indoor_temp_1","indoor_temp_2","temperature_inside"])
        val = _to_num(val)
        if pd.isna(val): return None, "temp missing"
        if op in ("이상","초과"):   return bool(val >= th), f"temp {val:.1f} ≥ {th}"
        if op in ("이하","이하면"): return bool(val <= th), f"temp {val:.1f} ≤ {th}"
        if op == "미만":           return bool(val <  th), f"temp {val:.1f} < {th}"

    # Humidity
    m = re.search(r"(?:습도|RH)[^\d]*(\d+(?:\.\d+)?)\s*%\s*(이상|이하면|이하|미만|초과)?", txt)
    if m:
        th = float(m.group(1)); op = m.group(2) or "이상"
        val = resolve_signal(row, mapping, ["avg_indoor_humidity","indoor_humidity_1","indoor_humidity_2","humidity_inside"])
        val = _to_num(val)
        if pd.isna(val): return None, "hum missing"
        if op in ("이상","초과"):   return bool(val >= th), f"hum {val:.1f}% ≥ {th}%"
        if op in ("이하","이하면"): return bool(val <= th), f"hum {val:.1f}% ≤ {th}%"
        if op == "미만":           return bool(val <  th), f"hum {val:.1f}% < {th}%"

    return None, "no numeric condition"


# ---------------- Timing FSM -----------------
@dataclass
class ActuatorTiming:
    delay_on_sec: int = 0   # 조건 True가 연속 이만큼 지속돼야 ON 전환
    delay_off_sec: int = 0  # 조건 False가 연속 이만큼 지속돼야 OFF 전환
    min_on_sec: int = 0     # ON으로 바뀐 뒤 최소 유지
    min_off_sec: int = 0    # OFF로 바뀐 뒤 최소 유지


class TimingFSM:
    def __init__(self, timing: ActuatorTiming):
        self.timing = timing
        self.last_state = 0              # 실제 출력된 최종 상태
        self.last_change_ts = None       # 최종 상태가 바뀐 시각
        self.pending_desired = None      # 대기 중인 희망 상태(지연 충족 대기)
        self.pending_since_ts = None     # 희망 상태가 시작된 시각

    def _sec(self, a, b):
        if pd.isna(a) or pd.isna(b): return None
        try: return float((a - b).total_seconds())
        except Exception: return None

    def step(self, ts: pd.Timestamp, desired: int, timing_override: ActuatorTiming|None=None):
        # 한 스텝만 적용할 타이밍(룰 텍스트에 의해 덮어쓰기)
        tcfg = timing_override if timing_override is not None else self.timing

        # 1) 최소 유지시간 락
        if self.last_change_ts is not None:
            elapsed = self._sec(ts, self.last_change_ts)
            if elapsed is not None:
                if self.last_state == 1 and tcfg.min_on_sec and elapsed < tcfg.min_on_sec:
                    return self.last_state, f"timing|min_on_lock {int(elapsed)}/{tcfg.min_on_sec}s"
                if self.last_state == 0 and tcfg.min_off_sec and elapsed < tcfg.min_off_sec:
                    return self.last_state, f"timing|min_off_lock {int(elapsed)}/{tcfg.min_off_sec}s"

        # 2) 희망 상태 == 현재 상태 → 대기 해제
        if desired == self.last_state:
            self.pending_desired = None
            self.pending_since_ts = None
            return self.last_state, "timing|stable"

        # 3) 지연 필요시간 계산
        need = tcfg.delay_on_sec if desired == 1 else tcfg.delay_off_sec
        if need <= 0 or pd.isna(ts):
            # 지연 필요없음 → 즉시 전환
            self.last_state = desired
            self.last_change_ts = ts
            self.pending_desired = None
            self.pending_since_ts = None
            return self.last_state, ("timing|no_delay" if need <= 0 else "timing|ts_na")

        # 4) 지연 디바운싱
        if self.pending_desired != desired:
            # 새 희망 상태 시작
            self.pending_desired = desired
            self.pending_since_ts = ts
            return self.last_state, f"timing|pending 0/{need}s"

        held = self._sec(ts, self.pending_since_ts)
        if held is not None and held >= need:
            # 지연 충족 → 전환 확정
            self.last_state = desired
            self.last_change_ts = ts
            self.pending_desired = None
            self.pending_since_ts = None
            return self.last_state, f"timing|held {int(held)}≥{need}s"
        else:
            h = int(held) if held is not None else 0
            return self.last_state, f"timing|hold {h}/{need}s"


# -------- Timing config: file + defaults + rule-text parser ---------

def load_actuator_timings(json_path: Path|None, default_timing: ActuatorTiming):
    per_act = {a: ActuatorTiming(**vars(default_timing)) for a in ACTUATORS}
    if json_path and json_path.exists():
        try:
            cfg = json.loads(json_path.read_text(encoding="utf-8"))
            for act, t in (cfg or {}).items():
                if act in per_act and isinstance(t, dict):
                    for k in ("delay_on_sec","delay_off_sec","min_on_sec","min_off_sec"):
                        if k in t:
                            setattr(per_act[act], k, int(t[k]))
        except Exception as e:
            print(f"[WARN] actuators.json 읽기 오류: {e}")
    return per_act


_TIME_UNIT = {"초":1, "sec":1, "s":1, "분":60, "min":60, "m":60}


def _to_seconds(num_str: str, unit_str: str) -> int:
    try:
        v = float(num_str)
    except Exception:
        return 0
    unit = unit_str.strip().lower()
    for k, mult in _TIME_UNIT.items():
        if unit.endswith(k):
            return int(round(v * mult))
    # default seconds if unit unknown
    return int(round(v))


def parse_timing_from_text(text: str) -> ActuatorTiming|None:
    """룰/전제 텍스트에서 delay/min 타이밍을 추출. 없으면 None 반환.
       규칙:
         - "지연 <숫자><단위> (후)? (ON/동작)"  → delay_on_sec
         - "지연 <숫자><단위> (후)? (OFF/정지/중지)" → delay_off_sec
         - "최소 (ON )?유지 <숫자><단위>" / "min on <숫자>[s|m]"  → min_on_sec
         - "최소 OFF 유지 <숫자><단위>" / "min off <숫자>[s|m]"   → min_off_sec
         - "지연 <숫자><단위>" (방향 미표시) → on/off 모두에 적용
    """
    if not text:
        return None
    txt = str(text)
    found = {}

    # 1) explicit ON delay
    for m in re.finditer(r"(?:지연|delay)\s*(\d+(?:\.\d+)?)\s*(초|분|s|sec|min|m)\s*(?:후)?\s*(?:ON|동작|켜|가동)", txt, flags=re.IGNORECASE):
        found['delay_on_sec'] = _to_seconds(m.group(1), m.group(2))

    # 2) explicit OFF delay
    for m in re.finditer(r"(?:지연|delay)\s*(\d+(?:\.\d+)?)\s*(초|분|s|sec|min|m)\s*(?:후)?\s*(?:OFF|정지|중지|꺼)", txt, flags=re.IGNORECASE):
        found['delay_off_sec'] = _to_seconds(m.group(1), m.group(2))

    # 3) ambiguous delay (no ON/OFF)
    for m in re.finditer(r"(?:지연|delay)\s*(\d+(?:\.\d+)?)\s*(초|분|s|sec|min|m)(?!\s*(후)?\s*(ON|OFF|동작|정지|중지|켜|꺼))", txt, flags=re.IGNORECASE):
        sec = _to_seconds(m.group(1), m.group(2))
        found.setdefault('delay_on_sec', sec)
        found.setdefault('delay_off_sec', sec)

    # 4) min ON hold
    for m in re.finditer(r"(?:최소\s*(?:ON\s*)?유지|min\s*on)\s*(\d+(?:\.\d+)?)\s*(초|분|s|sec|min|m)", txt, flags=re.IGNORECASE):
        found['min_on_sec'] = _to_seconds(m.group(1), m.group(2))

    # 5) min OFF hold
    for m in re.finditer(r"(?:최소\s*OFF\s*유지|min\s*off)\s*(\d+(?:\.\d+)?)\s*(초|분|s|sec|min|m)", txt, flags=re.IGNORECASE):
        found['min_off_sec'] = _to_seconds(m.group(1), m.group(2))

    if not found:
        return None

    return ActuatorTiming(
        delay_on_sec = int(found.get('delay_on_sec', 0)),
        delay_off_sec = int(found.get('delay_off_sec', 0)),
        min_on_sec    = int(found.get('min_on_sec', 0)),
        min_off_sec   = int(found.get('min_off_sec', 0)),
    )


def decide_actuator(row, band_code, act, rule_text, prem_text, mapping):
    # 1) Evaluate premise (very lightweight gates)
    prem_ok = True
    prem_reason = []
    if prem_text:
        if "비" in prem_text:  # rain stop
            rain = resolve_signal(row, mapping, ["rain_sensor"])
            ok = (pd.isna(rain) or _to_num(rain) == 0.0)
            prem_ok &= bool(ok); prem_reason.append(f"rain_ok={ok}")
        if "일사" in prem_text:  # daylight gate
            solar = resolve_signal(row, mapping, ["outdoor_solar"])
            ok = (not pd.isna(solar) and _to_num(solar) > 5.0)
            prem_ok &= bool(ok); prem_reason.append(f"daylight={ok}")
        # add other keywords → signals as needed

    # 2) Rule presence
    if not rule_text:
        return 0, f"no rule for {act} in {band_code}", None, ""

    # 3) Evaluate numeric condition (if any); else treat directive text
    cond_val, cond_reason = eval_condition_numeric(row, mapping, rule_text)
    if cond_val is None:
        txt = rule_text
        if "유지" in txt or "동작" in txt or "ON" in txt or "닫힘" in txt:
            cond_val, cond_reason = True, "directive"
        elif "열림" in txt or "OFF" in txt or "중지" in txt or "STOP" in txt or "정지" in txt:
            cond_val, cond_reason = False, "directive"
        else:
            cond_val, cond_reason = True, "no condition"

    # 4) Parse timing from rule/premise text (rule wins over premise if both specify)
    t_from_prem = parse_timing_from_text(prem_text or "")
    t_from_rule = parse_timing_from_text(rule_text or "")
    timing_override = t_from_rule or t_from_prem  # 우선순위: rule > premise
    timing_src = "rule" if t_from_rule else ("premise" if t_from_prem else "")

    # 5) Final desired state & base reason
    desired = 1 if (prem_ok and cond_val) else 0
    reason = f"prem_ok={prem_ok} [{' & '.join(prem_reason)}] | {cond_reason}"
    return desired, reason, timing_override, timing_src


# -----------------------------------------------------
# Main
# -----------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--x",   default=None, help="입력 CSV 경로(미지정 시 자동 탐색)")
    ap.add_argument("--out", default="rules_decisions.csv")
    ap.add_argument("--log", default="rules_transitions.log")
    ap.add_argument("--rules_xlsx", default=str(EXCEL_RULES_DEFAULT))
    ap.add_argument("--column_map",  default=str(COLUMN_MAP_DEFAULT))
    # timing defaults + per-actuator JSON
    ap.add_argument("--default_delay_on_sec", type=int, default=0)
    ap.add_argument("--default_delay_off_sec", type=int, default=0)
    ap.add_argument("--default_min_on_sec", type=int, default=0)
    ap.add_argument("--default_min_off_sec", type=int, default=0)
    ap.add_argument("--actuators_json", default=None)
    args = ap.parse_args()

    # ---- Auto-detect --x if omitted ----
    candidates = [
        args.x,  # user-provided first
        "./train_x.csv","./test_X.csv","./test_x.csv",
        "./data/train_x.csv","./data/test_X.csv","./data/test_x.csv"
    ]
    args.x = next((c for c in candidates if c and Path(c).exists()), None)
    if not args.x:
        print("CWD:", os.getcwd())
        print("ARGV:", sys.argv)
        print("Tried:", candidates)
        print("ERROR: 입력 CSV를 찾지 못했습니다. --x 경로를 명시하거나 data/ 폴더에 train_x.csv/test_X.csv를 두세요.")
        return  # 깔끔 종료 (traceback 없음)

    rules_path = Path(args.rules_xlsx)
    colmap_path = Path(args.column_map)
    mapping = load_column_mapping(colmap_path)

    # Load X
    try:
        X = pd.read_csv(args.x)
    except Exception as e:
        print(f"ERROR: 입력 CSV를 읽는 중 오류: {e}")
        return

    X = unify_timestamp(X, mapping)
    X = add_timebands(X)

    # Load rules from Excel (soft-fail)
    tidy = parse_excel_rules(rules_path)

    # Per-band, per-actuator lookup
    rules = {}
    if not tidy.empty:
        for _, r in tidy.iterrows():
            rules.setdefault(r["band"], {}).setdefault(
                r["actuator"], {"rule": r["rule"], "prem": r["premise"]}
            )

    # Timing configs
    default_timing = ActuatorTiming(
        delay_on_sec=args.default_delay_on_sec,
        delay_off_sec=args.default_delay_off_sec,
        min_on_sec=args.default_min_on_sec,
        min_off_sec=args.default_min_off_sec,
    )
    timings = load_actuator_timings(Path(args.actuators_json) if args.actuators_json else None, default_timing)
    fsms = {act: TimingFSM(timings[act]) for act in ACTUATORS}

    # Decide per row
    states  = {act: [] for act in ACTUATORS}
    reasons = {f"{act}_reason": [] for act in ACTUATORS}

    for _, row in X.iterrows():
        ts = row.get("timestamp", pd.NaT)
        b  = row.get("band_code", None)
        for act in ACTUATORS:
            rr = rules.get(b, {}).get(act, {"rule":"", "prem":""})
            desired, base_reason, timing_override, src = decide_actuator(row, b, act, rr["rule"], rr["prem"], mapping)
            # rule/premise 텍스트에서 파싱된 타이밍이 있으면 1-step override 적용
            final_state, timing_reason = fsms[act].step(ts, int(desired), timing_override)
            tag = f" | timing_src={src}" if src else ""
            states[act].append(final_state)
            reasons[f"{act}_reason"].append(f"{base_reason} | {timing_reason}{tag}")

    # Output decisions CSV
    out = pd.DataFrame({"timestamp": X["timestamp"], "band_code": X["band_code"]})
    for act in ACTUATORS:
        out[act] = states[act]
        out[f"{act}_reason"] = reasons[f"{act}_reason"]

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False, encoding="utf-8")

    # Transition log (state changes only)
    lines = []
    for act in ACTUATORS:
        prev = None
        for ts, band, st, rs in zip(out["timestamp"], out["band_code"], out[act], out[f"{act}_reason"]):
            if prev is None or st != prev:
                lines.append(f"{ts} [{band}] {act} -> {st} | {rs}")
                prev = st
    Path(args.log).write_text("\n".join(lines), encoding="utf-8")

    print(f"[OK] wrote {args.out} and {args.log}")


if __name__ == "__main__":
    main()
