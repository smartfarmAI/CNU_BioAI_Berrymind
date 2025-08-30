# -*- coding: utf-8 -*-
"""
Stateful greenhouse control (patched)
- Defaults: run with no args (uses local CSV filenames)
- Temporal logic: recheck / require-continuous / cooldown
- Improved parser:
  * ON/OFF synonyms: ON,OFF,켜,끄,가동,정지,중지,동작,작동,STOP
  * Inequality: 이상/이하/>=/<= handled per-threshold
  * CO2: "... Xppm 이하이면 Yppm 만족시킬때까지 동작" → ON<=X, OFF>=Y
  * Pulse: "열림모터 30초/닫힘모터 20초" → PULSE_OPEN/PULSE_CLOSE actions

Outputs:
  - x_control_plan_stateful.csv
  - cmd_log_stateful.csv
"""

import re
import argparse
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple
import numpy as np
import pandas as pd
from pathlib import Path

def read_csv_multienc(path: Path, **kwargs) -> pd.DataFrame:
    for enc in ("utf-8-sig","cp949","utf-8"):
        try:
            return pd.read_csv(path, encoding=enc, **kwargs)
        except Exception as e:
            last = e
    raise last

def load_logic_multiheader(path: Path) -> pd.DataFrame:
    try:
        df = read_csv_multienc(path, header=[0,1])
        if not isinstance(df.columns, pd.MultiIndex):
            raise ValueError("not multiindex")
    except Exception:
        raw = read_csv_multienc(path)
        if "time_class" not in raw.columns:
            raise RuntimeError("cmd_logic.csv에 'time_class' 컬럼이 필요합니다.")
        tuples: List[Tuple[str,str]] = []
        for c in raw.columns:
            if c in ("time_class","시간"):
                tuples.append((c,""))
            else:
                dev, kind = (c.split("_",1)+[""])[:2] if "_" in c else (c,"")
                tuples.append((dev, kind))
        df = raw.copy()
        df.columns = pd.MultiIndex.from_tuples(tuples, names=["device","kind"])

    time_key = None; desc_key = None
    for a,b in df.columns:
        if isinstance(b,str) and "time_class" in b.lower():
            time_key = (a,b)
        if b == "시간":
            desc_key = (a,b)
    if time_key is None:
        if ("time_class","") in df.columns:
            time_key = ("time_class","")
        else:
            for a,b in df.columns:
                if a == "time_class": time_key=(a,b); break
    assert time_key is not None, "cmd_logic.csv에 'time_class' 컬럼이 필요합니다."

    rules = df.copy()
    rules["time_class"] = rules[time_key]
    if desc_key:
        rules["time_desc"] = rules[desc_key]
        rules = rules.drop(columns=[time_key, desc_key])
    else:
        rules = rules.drop(columns=[time_key])
    return rules

def pick_first(cols: List[str], prefer: List[str]) -> Optional[str]:
    for p in prefer:
        for c in cols:
            if p.lower() in c.lower():
                return c
    return cols[0] if cols else None

@dataclass
class ParsedRule:
    unit: Optional[str] = None
    on: Optional[float] = None
    on_dir: Optional[str] = None   # 'ge' or 'le'
    off: Optional[float] = None
    off_dir: Optional[str] = None  # 'ge' or 'le'
    opening: Optional[float] = None
    dose_ml: Optional[float] = None
    moist_thr_pct: Optional[float] = None
    pulse_seconds: Optional[float] = None
    pulse_dir: Optional[str] = None  # 'open' or 'close'
    recheck_min: Optional[float] = None
    require_cont_min: Optional[float] = None
    cooldown_min: Optional[float] = None
    text_cond: str = ""
    text_prem: str = ""

def parse_temporal(text: str) -> Dict[str, float]:
    out = {}
    if not isinstance(text, str): return out
    m = re.search(r"(\d+(?:\.\d+)?)\s*분\s*(뒤|후)\s*(재측정|재확인|상태조회|체크|recheck)", text)
    if m: out["recheck_min"] = float(m.group(1))
    m = re.search(r"(\d+(?:\.\d+)?)\s*분\s*(유지|연속)", text)
    if m: out["require_cont_min"] = float(m.group(1))
    m = re.search(r"(?:PAUSE|지연|쿨다운|정지)\s*(\d+(?:\.\d+)?)\s*분", text, flags=re.I)
    if m: out["cooldown_min"] = float(m.group(1))
    # English
    m = re.search(r"(recheck|after)\s*(\d+(?:\.\d+)?)\s*min", text, flags=re.I)
    if m and "recheck_min" not in out: out["recheck_min"] = float(m.group(2))
    m = re.search(r"(hold|continuous)\s*(\d+(?:\.\d+)?)\s*min", text, flags=re.I)
    if m and "require_cont_min" not in out: out["require_cont_min"] = float(m.group(2))
    m = re.search(r"(pause|cooldown)\s*(\d+(?:\.\d+)?)\s*min", text, flags=re.I)
    if m and "cooldown_min" not in out: out["cooldown_min"] = float(m.group(2))
    return out

def parse_rule_text(cond_text: str, prem_text: str) -> ParsedRule:
    pr = ParsedRule(text_cond=str(cond_text) if isinstance(cond_text,str) else "",
                    text_prem=str(prem_text) if isinstance(prem_text,str) else "")
    t = pr.text_cond.strip()
    if not t: return pr

    tt = t.replace(" ", "")
    if "도" in tt: pr.unit = "C"
    elif "%" in tt: pr.unit = "%"
    elif "CO2" in t.upper() or "ppm" in tt: pr.unit = "ppm"
    elif "일사" in t or "solar" in t.lower(): pr.unit = "solar"

    # opening percent
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", t)
    if m: pr.opening = float(m.group(1))

    # irrigation
    m = re.search(r"함수율\s*(\d+(?:\.\d+)?)\s*%", t)
    if m: pr.moist_thr_pct = float(m.group(1))
    m = re.search(r"(\d+(?:\.\d+)?)\s*ml", t, flags=re.I)
    if m: pr.dose_ml = float(m.group(1))

    # pulse (motor seconds)
    if re.search(r"(열림|open)", t, flags=re.I) and re.search(r"(모터|motor)", t, flags=re.I):
        m = re.search(r"(\d+(?:\.\d+)?)\s*(?:초|sec|s)\s*(?:동안)?", t, flags=re.I)
        if m:
            pr.pulse_seconds = float(m.group(1)); pr.pulse_dir = "open"
    if re.search(r"(닫힘|close)", t, flags=re.I) and re.search(r"(모터|motor)", t, flags=re.I):
        m = re.search(r"(\d+(?:\.\d+)?)\s*(?:초|sec|s)\s*(?:동안)?", t, flags=re.I)
        if m:
            pr.pulse_seconds = float(m.group(1)); pr.pulse_dir = "close"

    # thresholds with inequality direction and ON/OFF synonyms
    # Recognize on/off words
    ON_WORDS  = r"(?:ON|켜|가동|동작|작동|start|START)"
    OFF_WORDS = r"(?:OFF|끄|정지|중지|STOP|stop)"
    # Patterns like: '20도 이상 ... ON/동작', '28 >= ON', '26 이하 ... OFF/정지/STOP'
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:도|%|ppm)?\s*(이상|>=|초과|이하|<=|미만).{0,20}?"+ON_WORDS, t)
    if m:
        pr.on = float(m.group(1))
        op = m.group(2)
        pr.on_dir = 'ge' if op in ("이상",">=","초과") else 'le'
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:도|%|ppm)?\s*(이상|>=|초과|이하|<=|미만).{0,20}?"+OFF_WORDS, t)
    if m:
        pr.off = float(m.group(1))
        op = m.group(2)
        pr.off_dir = 'ge' if op in ("이상",">=","초과") else 'le'

    # Minimal patterns like '28 >= ON 25 <= OFF'
    if pr.on is None:
        m = re.search(r"(>=|<=)\s*(\d+(?:\.\d+)?)\s*.*?"+ON_WORDS, t)
        if m:
            pr.on = float(m.group(2)); pr.on_dir = 'ge' if m.group(1)=='>=' else 'le'
    if pr.off is None:
        m = re.search(r"(>=|<=)\s*(\d+(?:\.\d+)?)\s*.*?"+OFF_WORDS, t)
        if m:
            pr.off = float(m.group(2)); pr.off_dir = 'ge' if m.group(1)=='>=' else 'le'

    # CO2 setpoint style: "Xppm 이하로 감지되면 Yppm(을) 만족시킬때까지 동작"
    m = re.search(r"(\d+(?:\.\d+)?)\s*ppm\s*(?:이하|<=|미만).*?(?:만족|유지).*?(\d+(?:\.\d+)?)\s*ppm", t, flags=re.I)
    if m:
        low = float(m.group(1)); target = float(m.group(2))
        pr.on = low; pr.on_dir = 'le'
        if pr.off is None:
            pr.off = target; pr.off_dir = 'ge'

    # Temporal
    pr.__dict__.update(parse_temporal(t))
    return pr

def premise_ok(prem_text: str, rain_val: float) -> bool:
    if not isinstance(prem_text, str) or not prem_text.strip():
        return True
    t = prem_text
    if "비" in t and ("금지" in t or "닫" in t or "정지" in t):
        if pd.notna(rain_val): return (rain_val == 0)
    return True

@dataclass
class DevState:
    last_value: Optional[float] = None
    last_action_time: Optional[pd.Timestamp] = None
    cooldown_until: Optional[pd.Timestamp] = None
    pending_due: Optional[pd.Timestamp] = None
    pending_kind: Optional[str] = None
    pending_target: Optional[float] = None
    cont_start: Optional[pd.Timestamp] = None

def run_engine(x_path: Path, logic_path: Path, out_plan: Path, out_log: Path,
               max_rows: int=0, progress_every: int=0, devices_filter: Optional[str]=None):
    rules_df = load_logic_multiheader(logic_path)

    x_df = read_csv_multienc(x_path)
    # time col
    time_col = "timestamp" if "timestamp" in x_df.columns else next((c for c in x_df.columns if "time" in c.lower() or "date" in c.lower()), None)
    if time_col is None:
        raise RuntimeError("시간열(timestamp/time/date)이 필요합니다.")
    x_df[time_col] = pd.to_datetime(x_df[time_col], errors="coerce")
    x_df = x_df.sort_values(time_col).reset_index(drop=True)
    if max_rows and len(x_df) > max_rows:
        x_df = x_df.iloc[:max_rows].copy()

    # sensors
    TEMP_COL = pick_first([c for c in x_df.columns if "temp" in c.lower() and "outdoor" not in c.lower()], ["avg_indoor_temp","indoor_temp"])
    HUM_COL  = pick_first([c for c in x_df.columns if "humidity" in c.lower()], ["avg_indoor_humidity","humidity"])
    CO2_COL  = pick_first([c for c in x_df.columns if "co2" in c.lower() and "conc" in c.lower()], ["co2_concentration"])
    SOLAR_COL= pick_first([c for c in x_df.columns if "solar" in c.lower() and "outdoor" in c.lower()], ["outdoor_solar"])
    RAIN_COL = pick_first([c for c in x_df.columns if "rain" in c.lower()], ["rain_sensor"])

    DEVICE_MAPPINGS = {
        "FCU": {"type":"binary", "sensor": TEMP_COL, "target_status":"target_fcu_status"},
        "FOG": {"type":"binary", "sensor": HUM_COL,  "target_status":"target_fog_status"},
        "CO2": {"type":"binary", "sensor": CO2_COL, "target_status":"target_co2_system_status"},
        "유동팬": {"type":"binary", "sensor": None, "target_status":"target_circulation_fan_status"},
        "상부차광스크린": {"type":"opening", "sensor": SOLAR_COL, "target_opening":"target_external_shade_opening", "target_pulse":"target_external_shade_pulse_seconds"},
        "상부보온커텐": {"type":"opening", "sensor": None, "target_opening":"target_horizontal_curtain_opening", "target_pulse":"target_horizontal_curtain_pulse_seconds"},
        "좌우천창": {"type":"opening", "sensor": TEMP_COL, "target_opening":"target_outer_window_opening", "target_pulse":"target_outer_window_pulse_seconds"},
        "양액기": {"type":"dose", "sensor": HUM_COL, "target_irrigation_ml":"target_irrigation_ml"},
    }

    all_devices = sorted(set([a for (a,b) in rules_df.columns if b in ("조건","대전제") and not str(a).startswith("Unnamed")]))
    # allow filter
    if devices_filter and devices_filter.strip():
        allow = {d.strip() for d in devices_filter.split(",")}
        devices = [d for d in all_devices if d in allow]
    else:
        devices = all_devices
    print(f"[DEVICES] {devices}")

    # compile rules
    compiled = {dev:{} for dev in all_devices}
    for _, r in rules_df.iterrows():
        tc = int(r["time_class"])
        for dev in all_devices:
            pr = parse_rule_text(r.get((dev,"조건"), ""), r.get((dev,"대전제"), ""))
            compiled[dev][tc] = pr

    out = x_df.copy()
    # create targets/trace columns
    for dev, meta in DEVICE_MAPPINGS.items():
        tcols = [k for k in meta.keys() if k.startswith("target_")]
        for k in tcols:
            out[meta[k]] = np.nan
        out[f"trace_{dev}"] = ""

    logs: List[Dict[str, Any]] = []
    def add_log(idx, device, action, value, prev, why, extra=None):
        logs.append({
            "timestamp": out.at[idx, time_col],
            "time_class": int(out.at[idx, "time_class"]) if "time_class" in out.columns else np.nan,
            "device": device,
            "action": action,
            "value": value,
            "prev_value": (prev if prev is not None else np.nan),
            "reason": why,
            **(extra or {})
        })

    t_arr  = out[time_col].values
    tc_arr = out["time_class"].values if "time_class" in out.columns else np.zeros(len(out), dtype=int)
    s_temp = out[TEMP_COL].values if TEMP_COL in out.columns else None
    s_hum  = out[HUM_COL].values  if HUM_COL  in out.columns else None
    s_co2  = out[CO2_COL].values  if CO2_COL  in out.columns else None
    s_sol  = out[SOLAR_COL].values if SOLAR_COL in out.columns else None
    s_rain = out[RAIN_COL].values if RAIN_COL in out.columns else None

    def sensor_value(idx, unit_hint, default_col):
        if unit_hint == "C" and s_temp is not None: return s_temp[idx], TEMP_COL
        if unit_hint == "%" and s_hum is not None: return s_hum[idx], HUM_COL
        if unit_hint == "ppm" and s_co2 is not None: return s_co2[idx], CO2_COL
        if unit_hint == "solar" and s_sol is not None: return s_sol[idx], SOLAR_COL
        # fallback
        if default_col and default_col in out.columns:
            return out.iat[idx, out.columns.get_loc(default_col)], default_col
        return np.nan, ""

    for dev in devices:
        meta = DEVICE_MAPPINGS.get(dev)
        if meta is None:
            print(f"[WARN] mapping 없음 → '{dev}' 건너뜀"); continue
        dtype = meta["type"]
        state = DevState()
        nrows = len(out)

        for i in range(nrows):
            if progress_every and (i % progress_every == 0):
                print(f"[{dev}] progress {i}/{nrows} ts={t_arr[i]}")
            ts = t_arr[i]; tc = int(tc_arr[i])
            rule = compiled.get(dev,{}).get(tc, ParsedRule())
            rain_val = s_rain[i] if s_rain is not None else np.nan
            premok = premise_ok(rule.text_prem, rain_val)
            if state.cooldown_until and ts < state.cooldown_until:
                continue

            sval, scol = sensor_value(i, rule.unit, meta.get("sensor"))
            desired = None; desired_kind = None
            extra = {"sensor":scol, "sensor_value":sval,
                     "threshold_on":rule.on, "threshold_off":rule.off,
                     "cond_text":rule.text_cond, "premise_text":rule.text_prem}

            if dtype == "binary":
                # ON condition
                if (rule.on is not None) and pd.notna(sval):
                    if (rule.on_dir=='le' and sval <= rule.on) or (rule.on_dir!='le' and sval >= rule.on):
                        desired = 1.0; desired_kind = "on"
                # OFF condition
                if (rule.off is not None) and pd.notna(sval):
                    if (rule.off_dir=='le' and sval <= rule.off) or (rule.off_dir!='le' and sval >= rule.off):
                        desired = 0.0; desired_kind = "off"

            elif dtype == "opening":
                # Pulse commands take precedence if present
                if rule.pulse_seconds and rule.pulse_dir:
                    desired = float(rule.pulse_seconds)
                    desired_kind = f"pulse_{rule.pulse_dir}"
                elif rule.opening is not None:
                    desired = float(rule.opening); desired_kind = "set_opening"
                else:
                    if (rule.on is not None) and pd.notna(sval):
                        if (rule.on_dir=='le' and sval <= rule.on) or (rule.on_dir!='le' and sval >= rule.on):
                            desired = 100.0; desired_kind = "open"
                    if (rule.off is not None) and pd.notna(sval):
                        if (rule.off_dir=='le' and sval <= rule.off) or (rule.off_dir!='le' and sval >= rule.off):
                            desired = 0.0; desired_kind = "close"

            elif dtype == "dose":
                if rule.dose_ml is not None:
                    if (rule.moist_thr_pct is not None) and (s_hum is not None):
                        if pd.notna(s_hum[i]) and s_hum[i] <= rule.moist_thr_pct:
                            desired = float(rule.dose_ml); desired_kind = "dose"
                    else:
                        desired = float(rule.dose_ml); desired_kind = "dose"

            # helpers
            def minutes_between(a,b): return (b-a).total_seconds()/60.0
            cond_true = (desired is not None)

            # require continuous
            if rule.require_cont_min and cond_true:
                if state.cont_start is None: state.cont_start = ts
                if minutes_between(state.cont_start, ts) + 1e-9 < rule.require_cont_min:
                    state.pending_due  = state.cont_start + pd.Timedelta(minutes=rule.require_cont_min)
                    state.pending_kind = f"cont_{desired_kind}"
                    state.pending_target = desired
                    cond_true = False
            else:
                if not cond_true: state.cont_start = None
                elif state.cont_start is None: state.cont_start = ts

            # recheck
            if rule.recheck_min and cond_true:
                state.pending_due  = ts + pd.Timedelta(minutes=rule.recheck_min)
                state.pending_kind = f"recheck_{desired_kind}"
                state.pending_target = desired
                cond_true = False

            # pending due?
            if state.pending_due and ts >= state.pending_due:
                if premok and (state.pending_target is not None):
                    if dtype == "binary":
                        col = meta["target_status"]; prev = state.last_value
                        out.iat[i, out.columns.get_loc(col)] = state.pending_target
                        state.last_value = state.pending_target; state.last_action_time = ts
                        if rule.cooldown_min: state.cooldown_until = ts + pd.Timedelta(minutes=rule.cooldown_min)
                        add_log(i, dev, "ON" if state.pending_target>=0.5 else "OFF", state.pending_target, prev,
                                f"pending({state.pending_kind}) executed", extra)
                    elif dtype == "opening":
                        prev = state.last_value
                        if state.pending_kind and state.pending_kind.startswith("recheck_pulse"):
                            pcol = meta.get("target_pulse")
                            if pcol: out.iat[i, out.columns.get_loc(pcol)] = state.pending_target
                            state.last_action_time = ts
                            if rule.cooldown_min: state.cooldown_until = ts + pd.Timedelta(minutes=rule.cooldown_min)
                            act = "PULSE_OPEN" if "open" in state.pending_kind else "PULSE_CLOSE"
                            add_log(i, dev, act, state.pending_target, prev, f"pending({state.pending_kind}) executed", extra)
                        else:
                            col = meta.get("target_opening"); 
                            if col:
                                out.iat[i, out.columns.get_loc(col)] = state.pending_target
                            state.last_value = state.pending_target; state.last_action_time = ts
                            if rule.cooldown_min: state.cooldown_until = ts + pd.Timedelta(minutes=rule.cooldown_min)
                            act = "OPEN" if state.pending_target>=99.5 else ("CLOSE" if state.pending_target<=0.5 else "SET_OPENING")
                            add_log(i, dev, act, state.pending_target, prev,
                                    f"pending({state.pending_kind}) executed", extra)
                    elif dtype == "dose":
                        col = meta["target_irrigation_ml"]; prev = state.last_value
                        out.iat[i, out.columns.get_loc(col)] = state.pending_target
                        state.last_value = state.pending_target; state.last_action_time = ts
                        if rule.cooldown_min: state.cooldown_until = ts + pd.Timedelta(minutes=rule.cooldown_min)
                        add_log(i, dev, "IRRIGATE", state.pending_target, prev,
                                f"pending({state.pending_kind}) executed", extra)
                else:
                    add_log(i, dev, "SKIP", np.nan, state.last_value,
                            f"pending({state.pending_kind}) canceled", extra)
                state.pending_due=None; state.pending_kind=None; state.pending_target=None

            # immediate execution
            if cond_true and premok and (desired is not None):
                if dtype == "binary":
                    col = meta["target_status"]; prev = state.last_value
                    if (prev is None) or (abs(desired - prev) >= 0.5):
                        out.iat[i, out.columns.get_loc(col)] = desired
                        state.last_value = desired; state.last_action_time = ts
                        if rule.cooldown_min: state.cooldown_until = ts + pd.Timedelta(minutes=rule.cooldown_min)
                        add_log(i, dev, "ON" if desired>=0.5 else "OFF", desired, prev, "immediate", extra)
                elif dtype == "opening":
                    prev = state.last_value
                    if desired_kind and desired_kind.startswith("pulse_"):
                        # log pulse
                        pcol = meta.get("target_pulse")
                        if pcol: out.iat[i, out.columns.get_loc(pcol)] = desired
                        state.last_action_time = ts
                        if rule.cooldown_min: state.cooldown_until = ts + pd.Timedelta(minutes=rule.cooldown_min)
                        act = "PULSE_OPEN" if desired_kind.endswith("open") else "PULSE_CLOSE"
                        add_log(i, dev, act, desired, prev, "immediate", extra)
                    else:
                        col = meta.get("target_opening")
                        if col:
                            # write if significant change or first set
                            if (prev is None) or (abs(float(desired) - float(prev)) >= 1.0):
                                out.iat[i, out.columns.get_loc(col)] = desired
                                state.last_value = desired; state.last_action_time = ts
                                if rule.cooldown_min: state.cooldown_until = ts + pd.Timedelta(minutes=rule.cooldown_min)
                                act = "OPEN" if desired>=99.5 else ("CLOSE" if desired<=0.5 else "SET_OPENING")
                                add_log(i, dev, act, desired, prev, "immediate", extra)
                elif dtype == "dose":
                    col = meta["target_irrigation_ml"]; prev = state.last_value
                    if desired>0:
                        out.iat[i, out.columns.get_loc(col)] = desired
                        state.last_value = desired; state.last_action_time = ts
                        if rule.cooldown_min: state.cooldown_until = ts + pd.Timedelta(minutes=rule.cooldown_min)
                        add_log(i, dev, "IRRIGATE", desired, prev, "immediate", extra)

    out.to_csv(out_plan, index=False, encoding="utf-8-sig")
    pd.DataFrame(logs).to_csv(out_log, index=False, encoding="utf-8-sig")
    print(f"[SAVE] {out_plan} ; shape={out.shape}")
    print(f"[SAVE] {out_log}  ; events={len(logs)}")

def main():
    script_dir = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--x", type=str, default=str(script_dir / "x_train_with_time_class.csv"))
    ap.add_argument("--logic", type=str, default=str(script_dir / "cmd_logic.csv"))
    ap.add_argument("--out-plan", type=str, default=str(script_dir / "x_control_plan_stateful.csv"))
    ap.add_argument("--out-log", type=str, default=str(script_dir / "cmd_log_stateful.csv"))
    ap.add_argument("--max-rows", type=int, default=0)
    ap.add_argument("--progress-every", type=int, default=0)
    ap.add_argument("--devices", type=str, default="")
    args = ap.parse_args()

    x_path = Path(args.x); logic_path = Path(args.logic)
    out_plan = Path(args.out_plan); out_log = Path(args.out_log)

    if not x_path.exists():
        print(f"[ERROR] 데이터 파일을 찾을 수 없습니다: {x_path}"); return
    if not logic_path.exists():
        print(f"[ERROR] 로직 파일을 찾을 수 없습니다: {logic_path}"); return

    run_engine(x_path, logic_path, out_plan, out_log,
               max_rows=args.max_rows, progress_every=args.progress_every, devices_filter=args.devices)

if __name__ == "__main__":
    main()
