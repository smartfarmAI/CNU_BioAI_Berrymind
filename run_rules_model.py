#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Rules-only ON/OFF executor (SR/SS = TODO placeholders)

- Reads X data (CSV: train_x.csv or test_X.csv)
- Parses '인공지능 모델.xlsx' (band × actuator, rule/premise)  # 없으면 경고만 출력하고 계속
- Computes timeband (hour fallback; SR/SS placeholders left as TODO)
- For each timestamp and actuator, outputs ON/OFF (0/1) and a short reason
- Writes:
    1) decisions CSV  (timestamp, band_code, <ACT>, <ACT>_reason, ...)
    2) transition log (state-change lines only)

Usage:
  python run_rules_model.py --x ./data/train_x.csv --out ./out/decisions.csv --log ./out/transitions.log
"""
import argparse, re, json, os, sys
from pathlib import Path
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
    if 6 <= h <= 8:   return 1  # t1
    if 9 <= h <= 11:  return 2  # t2
    if 12 <= h <= 14: return 3  # t3
    if 15 <= h <= 17: return 4  # t4
    if 18 <= h <= 20: return 5  # t5
    if 21 <= h <= 23: return 6  # t6
    if 0 <= h <= 2:   return 7  # t7
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
        return 0, f"no rule for {act} in {band_code}"

    # 3) Evaluate numeric condition (if any); else treat directive text
    cond_val, cond_reason = eval_condition_numeric(row, mapping, rule_text)
    if cond_val is None:
        txt = rule_text
        if "유지" in txt or "동작" in txt or "ON" in txt or "닫힘" in txt:
            cond_val, cond_reason = True, "directive"
        elif "열림" in txt or "OFF" in txt or "중지" in txt or "STOP" in txt:
            cond_val, cond_reason = False, "directive"
        else:
            cond_val, cond_reason = True, "no condition"

    # 4) Final state
    state = 1 if (prem_ok and cond_val) else 0
    reason = f"prem_ok={prem_ok} [{' & '.join(prem_reason)}] | {cond_reason}"
    return state, reason

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

    # Decide per row
    states  = {act: [] for act in ACTUATORS}
    reasons = {f"{act}_reason": [] for act in ACTUATORS}

    for _, row in X.iterrows():
        b = row.get("band_code", None)
        for act in ACTUATORS:
            rr = rules.get(b, {}).get(act, {"rule":"", "prem":""})
            st, rs = decide_actuator(row, b, act, rr["rule"], rr["prem"], mapping)
            states[act].append(st)
            reasons[f"{act}_reason"].append(rs)

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
