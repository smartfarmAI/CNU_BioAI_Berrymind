# -*- coding: utf-8 -*-
"""
Stateful, time-aware greenhouse control engine (defaults built-in)

- 인자 없이 실행해도 동작합니다.
  기본 파일명(스크립트와 같은 폴더):
    --x         x_train_with_time_class.csv
    --logic     cmd_logic.csv
    --out-plan  x_control_plan_stateful.csv
    --out-log   cmd_log_stateful.csv

- 시간 로직 지원:
  * recheck: "N분 뒤 재측정/상태조회"
  * require continuous: "N분 유지/연속"
  * cooldown / PAUSE: "PAUSE N분", "N분 지연/쿨다운/정지"

- 진행률/장치필터:
  * --progress-every N   (N행마다 진행률 출력, 기본 0=끄기)
  * --devices "FCU,좌우천창" (지정 장치만 실행, 기본 전체)

사용 예)
  python control.py
  python control.py --progress-every 20000 --devices "FCU,좌우천창"
  python control.py --x "./x_train_with_time_class.csv" --logic "./cmd_logic.csv"
"""

import re
import argparse
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple
import numpy as np
import pandas as pd
from pathlib import Path

# -----------------------------
# 파일 로더 유틸
# -----------------------------
def read_csv_multienc(path: Path, **kwargs) -> pd.DataFrame:
    encs = ["utf-8-sig", "cp949", "utf-8"]
    last_err = None
    for enc in encs:
        try:
            return pd.read_csv(path, encoding=enc, **kwargs)
        except Exception as e:
            last_err = e
    raise last_err

def load_logic_multiheader(path: Path) -> pd.DataFrame:
    # 멀티헤더(장치 / [대전제|조건|…]) 가정, 실패 시 단일 헤더 폴백
    try:
        df = read_csv_multienc(path, header=[0,1])
        # header=[0,1] 성공 시 MultiIndex일 것
        if not isinstance(df.columns, pd.MultiIndex):
            raise ValueError("not a MultiIndex header")
    except Exception:
        # 폴백: 단일 헤더로 읽고, (장치, kind)로 재구성 시도
        raw = read_csv_multienc(path)
        # 최소한 time_class는 있어야 한다
        if "time_class" not in raw.columns:
            raise RuntimeError("cmd_logic.csv에 'time_class' 컬럼이 필요합니다.")
        # 단일 헤더인 경우, 장치별 '조건'/'대전제' 컬럼명이 예: 'FCU_조건' 형식이라고 가정
        tuples: List[Tuple[str,str]] = []
        for c in raw.columns:
            if c == "time_class" or c == "시간":
                tuples.append((c, ""))  # 메타
            else:
                if "_" in c:
                    dev, kind = c.split("_", 1)
                else:
                    dev, kind = c, ""
                tuples.append((dev, kind))
        df = raw.copy()
        df.columns = pd.MultiIndex.from_tuples(tuples, names=["device", "kind"])

    # time_class 키 찾기
    time_key = None; desc_key = None
    for a, b in df.columns:
        if isinstance(b, str) and "time_class" in b.lower():
            time_key = (a, b)
        if b == "시간":
            desc_key = (a, b)
    if time_key is None:
        # 일부 테이블은 최상위에 time_class가 있을 수 있음
        if ("time_class", "") in df.columns:
            time_key = ("time_class", "")
        else:
            # 완전 단일 컬럼일 수도 있으니 마지막 시도
            for a, b in df.columns:
                if a == "time_class":
                    time_key = (a, b); break
    assert time_key is not None, "cmd_logic.csv에 'time_class' 컬럼이 필요합니다."

    rules = df.copy()
    rules["time_class"] = rules[time_key]
    if desc_key:
        rules["time_desc"] = rules[desc_key]
        rules = rules.drop(columns=[time_key, desc_key])
    else:
        rules = rules.drop(columns=[time_key])
    return rules

# -----------------------------
# 보조 유틸
# -----------------------------
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
    off: Optional[float] = None
    opening: Optional[float] = None
    dose_ml: Optional[float] = None
    moist_thr_pct: Optional[float] = None
    recheck_min: Optional[float] = None
    require_cont_min: Optional[float] = None
    cooldown_min: Optional[float] = None
    text_cond: str = ""
    text_prem: str = ""

def parse_temporal(text: str) -> Dict[str, float]:
    out = {}
    if not isinstance(text, str): return out
    # 한국어
    m = re.search(r"(\d+(?:\.\d+)?)\s*분\s*(뒤|후)\s*(재측정|재확인|상태조회|체크|recheck)", text)
    if m: out["recheck_min"] = float(m.group(1))
    m = re.search(r"(\d+(?:\.\d+)?)\s*분\s*(유지|연속)", text)
    if m: out["require_cont_min"] = float(m.group(1))
    m = re.search(r"(?:PAUSE|지연|쿨다운|정지)\s*(\d+(?:\.\d+)?)\s*분", text, flags=re.I)
    if m: out["cooldown_min"] = float(m.group(1))
    # 영어
    m = re.search(r"(recheck|after)\s*(\d+(?:\.\d+)?)\s*min", text, flags=re.I)
    if m and "recheck_min" not in out: out["recheck_min"] = float(m.group(2))
    m = re.search(r"(hold|continuous)\s*(\d+(?:\.\d+)?)\s*min", text, flags=re.I)
    if m and "require_cont_min" not in out: out["require_cont_min"] = float(m.group(2))
    m = re.search(r"(pause|cooldown)\s*(\d+(?:\.\d+)?)\s*min", text, flags=re.I)
    if m and "cooldown_min" not in out: out["cooldown_min"] = float(m.group(2))
    return out

def parse_rule_text(cond_text: str, prem_text: str) -> ParsedRule:
    pr = ParsedRule(text_cond=str(cond_text) if isinstance(cond_text, str) else "",
                    text_prem=str(prem_text) if isinstance(prem_text, str) else "")
    t = pr.text_cond
    if not t: return pr

    tt = t.replace(" ", "")
    if "도" in tt: pr.unit = "C"
    elif "%" in tt: pr.unit = "%"
    elif "CO2" in t.upper() or "ppm" in tt: pr.unit = "ppm"
    elif "일사" in t or "solar" in t.lower(): pr.unit = "solar"

    # 개폐율/양액
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", t)
    if m: pr.opening = float(m.group(1))
    m = re.search(r"함수율\s*(\d+(?:\.\d+)?)\s*%", t)
    if m: pr.moist_thr_pct = float(m.group(1))
    m = re.search(r"(\d+(?:\.\d+)?)\s*ml", t, flags=re.I)
    if m: pr.dose_ml = float(m.group(1))

    # ON/OFF 임계
    num = r"(\d+(?:\.\d+)?)"
    ON_WORDS  = r"(?:ON|켜|가동)"
    OFF_WORDS = r"(?:OFF|끄|정지)"
    on_matches  = re.findall(rf"{num}(?:도|%|ppm)?(?:>=|이상|초과)?(?:.*?){ON_WORDS}", t)
    off_matches = re.findall(rf"{num}(?:도|%|ppm)?(?:<=|이하|미만)?(?:.*?){OFF_WORDS}", t)
    on_matches += re.findall(rf"(?:>=|이상){num}.*?{ON_WORDS}", t)
    off_matches+= re.findall(rf"(?:<=|이하){num}.*?{OFF_WORDS}", t)
    if on_matches:  pr.on  = float(on_matches[0])
    if off_matches: pr.off = float(off_matches[0])

    # 시간 로직
    pr.__dict__.update(parse_temporal(t))
    return pr

def premise_ok(prem_text: str, rain_val: float) -> bool:
    if not isinstance(prem_text, str) or not prem_text.strip():
        return True
    t = prem_text
    # 예: "비 오면 닫음/금지/정지"
    if "비" in t and ("금지" in t or "닫" in t or "정지" in t):
        if pd.notna(rain_val):
            return (rain_val == 0)
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

# -----------------------------
# 메인 엔진
# -----------------------------
def run_engine(x_path: Path, logic_path: Path, out_plan: Path, out_log: Path,
               max_rows: int=0, progress_every: int=0, devices_filter: Optional[str]=None):
    rules_df = load_logic_multiheader(logic_path)

    # 센서/시간 로드
    x_df = read_csv_multienc(x_path)
    # timestamp 열 찾기
    time_col = None
    if "timestamp" in x_df.columns:
        time_col = "timestamp"
    else:
        for c in x_df.columns:
            cl = c.lower()
            if ("time" in cl) or ("date" in cl):
                time_col = c; break
    if time_col is None:
        raise RuntimeError("시간열(timestamp/time/date)이 필요합니다.")
    x_df[time_col] = pd.to_datetime(x_df[time_col], errors="coerce")
    x_df = x_df.sort_values(time_col).reset_index(drop=True)
    if max_rows and len(x_df) > max_rows:
        x_df = x_df.iloc[:max_rows].copy()

    # 센서 컬럼 추정
    def find_cols(key_sub):
        return [c for c in x_df.columns if key_sub in c.lower()]
    TEMP_COL = pick_first([c for c in x_df.columns if ("temp" in c.lower()) and ("outdoor" not in c.lower())],
                          ["avg_indoor_temp","indoor_temp"])
    HUM_COL  = pick_first(find_cols("humidity"), ["avg_indoor_humidity","humidity"])
    CO2_COL  = pick_first([c for c in x_df.columns if "co2" in c.lower() and "conc" in c.lower()],
                          ["co2_concentration"])
    SOLAR_COL= pick_first([c for c in x_df.columns if "solar" in c.lower() and "outdoor" in c.lower()],
                          ["outdoor_solar"])
    RAIN_COL = pick_first(find_cols("rain"), ["rain_sensor"])

    DEVICE_MAPPINGS = {
        "FCU": {"target_status": "target_fcu_status", "sensor": TEMP_COL, "type":"binary"},
        "FOG": {"target_status": "target_fog_status", "sensor": HUM_COL,  "type":"binary"},
        "CO2": {"target_status": "target_co2_system_status", "sensor": CO2_COL, "type":"binary"},
        "유동팬": {"target_status":"target_circulation_fan_status", "sensor": None, "type":"binary"},
        "상부차광스크린": {"target_opening": "target_external_shade_opening", "sensor": SOLAR_COL, "type":"opening"},
        "상부보온커텐": {"target_opening": "target_horizontal_curtain_opening", "sensor": None, "type":"opening"},
        "좌우천창": {"target_opening": "target_outer_window_opening", "sensor": TEMP_COL, "type":"opening"},
        "양액기": {"target_irrigation_ml": "target_irrigation_ml", "sensor": HUM_COL, "type":"dose"},
    }

    # 장치 목록/필터
    all_devices = sorted(set([a for (a,b) in rules_df.columns
                              if b in ("조건","대전제") and not str(a).startswith("Unnamed")]))
    if devices_filter and devices_filter.strip():
        allow = {d.strip() for d in devices_filter.split(",")}
        devices = [d for d in all_devices if d in allow]
    else:
        devices = all_devices
    print(f"[DEVICES] {devices}")

    # 규칙 컴파일 (time_class별)
    compiled = {dev:{} for dev in all_devices}
    for _, r in rules_df.iterrows():
        tc = int(r["time_class"])
        for dev in all_devices:
            cond = r.get((dev,"조건"), "")
            prem = r.get((dev,"대전제"), "")
            compiled[dev][tc] = parse_rule_text(cond, prem)

    # 출력 프레임 준비
    out = x_df.copy()
    for dev, meta in DEVICE_MAPPINGS.items():
        for k, v in meta.items():
            if k.startswith("target_"):
                out[v] = np.nan
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

    # 벡터 캐시
    t_arr  = out[time_col].values
    tc_arr = out["time_class"].values if "time_class" in out.columns else np.zeros(len(out), dtype=int)
    s_temp = out[TEMP_COL].values if TEMP_COL in out.columns else None
    s_hum  = out[HUM_COL].values  if HUM_COL  in out.columns else None
    s_co2  = out[CO2_COL].values  if CO2_COL  in out.columns else None
    s_sol  = out[SOLAR_COL].values if SOLAR_COL in out.columns else None
    s_rain = out[RAIN_COL].values if RAIN_COL in out.columns else None

    # 장치 루프
    for dev in devices:
        meta = DEVICE_MAPPINGS.get(dev)
        if meta is None:
            print(f"[WARN] mapping 없음 → '{dev}' 건너뜀")
            continue
        dtype = meta["type"]
        state = DevState()

        def sensor_value(idx, unit_hint):
            if unit_hint == "C" and s_temp is not None: return s_temp[idx], TEMP_COL
            if unit_hint == "%" and s_hum  is not None: return s_hum[idx],  HUM_COL
            if unit_hint == "ppm" and s_co2 is not None: return s_co2[idx], CO2_COL
            if unit_hint == "solar" and s_sol is not None: return s_sol[idx], SOLAR_COL
            col = meta.get("sensor")
            val = out.iat[idx, out.columns.get_loc(col)] if (col and col in out.columns) else np.nan
            return val, (col or "")

        nrows = len(out)
        for i in range(nrows):
            if progress_every and (i % progress_every == 0):
                print(f"[{dev}] progress {i}/{nrows} ts={t_arr[i]}")
            ts = t_arr[i]
            tc = int(tc_arr[i])
            rule = compiled.get(dev, {}).get(tc, ParsedRule())
            rain_val = s_rain[i] if s_rain is not None else np.nan
            premok = premise_ok(rule.text_prem, rain_val)

            # 쿨다운
            if state.cooldown_until and ts < state.cooldown_until:
                continue

            sval, scol = sensor_value(i, rule.unit)
            desired = None; desired_kind = None

            # 즉시 조건평가
            if dtype == "binary":
                if (rule.on is not None) and pd.notna(sval) and sval >= rule.on:
                    desired = 1.0; desired_kind = "on"
                if (rule.off is not None) and pd.notna(sval) and sval <= rule.off:
                    desired = 0.0; desired_kind = "off"
            elif dtype == "opening":
                if rule.opening is not None:
                    desired = float(rule.opening); desired_kind = "set_opening"
                else:
                    if (rule.on is not None) and pd.notna(sval) and sval >= rule.on:
                        desired = 100.0; desired_kind = "open"
                    if (rule.off is not None) and pd.notna(sval) and sval <= rule.off:
                        desired = 0.0; desired_kind = "close"
            elif dtype == "dose":
                if rule.dose_ml is not None:
                    if (rule.moist_thr_pct is not None) and (s_hum is not None):
                        if pd.notna(s_hum[i]) and s_hum[i] <= rule.moist_thr_pct:
                            desired = float(rule.dose_ml); desired_kind = "dose"
                    else:
                        desired = float(rule.dose_ml); desired_kind = "dose"

            def minutes_between(a, b): return (b - a).total_seconds()/60.0
            cond_true = desired is not None

            # N분 유지(디바운스)
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

            # recheck N분
            if rule.recheck_min and cond_true:
                state.pending_due  = ts + pd.Timedelta(minutes=rule.recheck_min)
                state.pending_kind = f"recheck_{desired_kind}"
                state.pending_target = desired
                cond_true = False

            # pending 기한 도달 → 실행/취소
            if state.pending_due and ts >= state.pending_due:
                if premok and (state.pending_target is not None):
                    if dtype == "binary":
                        col = meta["target_status"]; prev = state.last_value
                        out.iat[i, out.columns.get_loc(col)] = state.pending_target
                        state.last_value = state.pending_target; state.last_action_time = ts
                        if rule.cooldown_min: state.cooldown_until = ts + pd.Timedelta(minutes=rule.cooldown_min)
                        add_log(i, dev, "ON" if state.pending_target>=0.5 else "OFF",
                                state.pending_target, prev, f"pending({state.pending_kind}) executed",
                                {"sensor":scol,"sensor_value":sval,"threshold_on":rule.on,"threshold_off":rule.off,
                                 "cond_text":rule.text_cond,"premise_text":rule.text_prem})
                    elif dtype == "opening":
                        col = meta["target_opening"]; prev = state.last_value
                        out.iat[i, out.columns.get_loc(col)] = state.pending_target
                        state.last_value = state.pending_target; state.last_action_time = ts
                        if rule.cooldown_min: state.cooldown_until = ts + pd.Timedelta(minutes=rule.cooldown_min)
                        act = "OPEN" if state.pending_target>=99.5 else ("CLOSE" if state.pending_target<=0.5 else "SET_OPENING")
                        add_log(i, dev, act, state.pending_target, prev, f"pending({state.pending_kind}) executed",
                                {"sensor":scol,"sensor_value":sval,"threshold_on":rule.on,"threshold_off":rule.off,
                                 "cond_text":rule.text_cond,"premise_text":rule.text_prem})
                    elif dtype == "dose":
                        col = meta["target_irrigation_ml"]; prev = state.last_value
                        out.iat[i, out.columns.get_loc(col)] = state.pending_target
                        state.last_value = state.pending_target; state.last_action_time = ts
                        if rule.cooldown_min: state.cooldown_until = ts + pd.Timedelta(minutes=rule.cooldown_min)
                        add_log(i, dev, "IRRIGATE", state.pending_target, prev, f"pending({state.pending_kind}) executed",
                                {"sensor":scol,"sensor_value":sval,"threshold_on":rule.on,"threshold_off":rule.off,
                                 "cond_text":rule.text_cond,"premise_text":rule.text_prem})
                else:
                    add_log(i, dev, "SKIP", np.nan, state.last_value,
                            f"pending({state.pending_kind}) canceled",
                            {"sensor":scol,"sensor_value":sval,"threshold_on":rule.on,"threshold_off":rule.off,
                             "cond_text":rule.text_cond,"premise_text":rule.text_prem})
                state.pending_due = None; state.pending_kind=None; state.pending_target=None

            # 즉시 실행 (pending 조건 없고, premise OK)
            if cond_true and premok and (desired is not None):
                if dtype == "binary":
                    col = meta["target_status"]; prev = state.last_value
                    if (prev is None) or (abs(desired - prev) >= 0.5):
                        out.iat[i, out.columns.get_loc(col)] = desired
                        state.last_value = desired; state.last_action_time = ts
                        if rule.cooldown_min: state.cooldown_until = ts + pd.Timedelta(minutes=rule.cooldown_min)
                        add_log(i, dev, "ON" if desired>=0.5 else "OFF", desired, prev, "immediate",
                                {"sensor":scol,"sensor_value":sval,"threshold_on":rule.on,"threshold_off":rule.off,
                                 "cond_text":rule.text_cond,"premise_text":rule.text_prem})
                elif dtype == "opening":
                    col = meta["target_opening"]; prev = state.last_value
                    if (prev is None) or (abs(desired - prev) >= 1.0):
                        out.iat[i, out.columns.get_loc(col)] = desired
                        state.last_value = desired; state.last_action_time = ts
                        if rule.cooldown_min: state.cooldown_until = ts + pd.Timedelta(minutes=rule.cooldown_min)
                        act = "OPEN" if desired>=99.5 else ("CLOSE" if desired<=0.5 else "SET_OPENING")
                        add_log(i, dev, act, desired, prev, "immediate",
                                {"sensor":scol,"sensor_value":sval,"threshold_on":rule.on,"threshold_off":rule.off,
                                 "cond_text":rule.text_cond,"premise_text":rule.text_prem})
                elif dtype == "dose":
                    col = meta["target_irrigation_ml"]; prev = state.last_value
                    if desired>0:
                        out.iat[i, out.columns.get_loc(col)] = desired
                        state.last_value = desired; state.last_action_time = ts
                        if rule.cooldown_min: state.cooldown_until = ts + pd.Timedelta(minutes=rule.cooldown_min)
                        add_log(i, dev, "IRRIGATE", desired, prev, "immediate",
                                {"sensor":scol,"sensor_value":sval,"threshold_on":rule.on,"threshold_off":rule.off,
                                 "cond_text":rule.text_cond,"premise_text":rule.text_prem})

    # 저장
    out.to_csv(out_plan, index=False, encoding="utf-8-sig")
    pd.DataFrame(logs).to_csv(out_log, index=False, encoding="utf-8-sig")
    print(f"[SAVE] {out_plan} ; shape={out.shape}")
    print(f"[SAVE] {out_log}  ; events={len(logs)}")

# -----------------------------
# 엔트리포인트 (모든 인자 선택형, 기본값은 스크립트 폴더 기준)
# -----------------------------
def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--x", type=str, default=str("x_train_with_time_class.csv"),
                    help="입력 데이터 CSV (기본: /x_train_with_time_class.csv)")
    ap.add_argument("--logic", type=str, default=str("cmd_logic.csv"),
                    help="제어 로직 CSV (기본: /cmd_logic.csv)")
    ap.add_argument("--out-plan", type=str, default=str("x_control_plan_stateful.csv"),
                    help="출력: 상태 기반 플랜 (기본: /x_control_plan_stateful.csv)")
    ap.add_argument("--out-log", type=str, default=str("cmd_log_stateful.csv"),
                    help="출력: 이벤트 로그 (기본: /cmd_log_stateful.csv)")
    ap.add_argument("--max-rows", type=int, default=0, help="0=전체, 그 외 상위 N행만")
    ap.add_argument("--progress-every", type=int, default=0, help="N행마다 진행률 출력(0=끄기)")
    ap.add_argument("--devices", type=str, default="", help="쉼표로 구분된 장치 이름만 실행 (예: 'FCU,좌우천창')")
    args = ap.parse_args()

    # 경로 객체화
    x_path = Path(args.x)
    logic_path = Path(args.logic)
    out_plan = Path(args.out_plan)
    out_log  = Path(args.out_log)

    # 존재 검사(입력만)
    if not x_path.exists():
        print(f"[ERROR] 데이터 파일을 찾을 수 없습니다: {x_path}")
        return
    if not logic_path.exists():
        print(f"[ERROR] 로직 파일을 찾을 수 없습니다: {logic_path}")
        return

    run_engine(
        x_path=x_path,
        logic_path=logic_path,
        out_plan=out_plan,
        out_log=out_log,
        max_rows=args.max_rows,
        progress_every=args.progress_every,
        devices_filter=args.devices
    )

if __name__ == "__main__":
    main()
