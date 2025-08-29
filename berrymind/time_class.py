# -*- coding: utf-8 -*-
# (재실행) 위 셀의 코드가 초기화되어 다시 실행합니다.

import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

SR_HOUR     = 6        # 일출 시(hour)
SS_HOUR     = 18       # 일몰 시(hour)
DELTA_HOURS = 3.0      # Δ 시간폭(시간)

ORIG = Path("./x_train.csv")
OUT  = Path("./x_train_with_time_class.csv")

def read_csv_safely(path: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig","utf-8","cp949"):
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception as e:
            last_err = e
    raise last_err

def detect_time_col(df: pd.DataFrame) -> str:
    pri = [c for c in df.columns if any(k in str(c).lower()
           for k in ["time","timestamp","date","datetime","측정","일시","시각","시간","저장시간"])]
    cand = None; best_frac=-1.0; best_uniq=-1
    for c in list(dict.fromkeys(pri + list(df.columns))):
        try:
            s = pd.to_datetime(df[c], errors="coerce", infer_datetime_format=True)
            frac = 1 - s.isna().mean()
            uniq = s.nunique(dropna=True)
            if frac > best_frac and uniq >= 100:
                cand, best_frac, best_uniq = c, frac, uniq
        except Exception:
            pass
    if cand is None:
        raise RuntimeError("시간열 자동 탐지 실패. -- time 컬럼명을 확인하세요.")
    return cand

def build_boundaries_for_date(date_obj, delta_hours, sr_hour, ss_hour):
    day_start = pd.Timestamp(datetime.combine(date_obj, datetime.min.time()))
    noon      = day_start + timedelta(hours=12)
    day_end   = day_start + timedelta(days=1)
    SR        = day_start + timedelta(hours=sr_hour)
    SS        = day_start + timedelta(hours=ss_hour)
    delta     = pd.Timedelta(hours=float(delta_hours))
    bps = [
        day_start, SR - delta, SR, SR + delta, noon, SS - delta, SS, SS + delta, day_end
    ]
    out = [bps[0]]
    for x in bps[1:]:
        out.append(max(x, out[-1]))
    return out

def assign_time_class_for_day(sub_df, time_col, b):
    t = sub_df[time_col].values
    cls = np.zeros(len(sub_df), dtype=np.int8)
    m7 = (t >= b[0]) & (t < b[1])
    m8 = (t >= b[1]) & (t < b[2])
    m1 = (t >= b[2]) & (t < b[3])
    m2 = (t >= b[3]) & (t < b[4])
    m3 = (t >= b[4]) & (t < b[5])
    m4 = (t >= b[5]) & (t < b[6])
    m5 = (t >= b[6]) & (t < b[7])
    m6 = (t >= b[7]) & (t < b[8])
    cls[m1] = 1; cls[m2] = 2; cls[m3] = 3; cls[m4] = 4
    cls[m5] = 5; cls[m6] = 6; cls[m7] = 7; cls[m8] = 8
    cls[cls == 0] = 3
    return pd.Series(cls, index=sub_df.index, name="time_class")

assert ORIG.exists(), f"원본 파일 없음: {ORIG}"
df = read_csv_safely(ORIG)
time_col = detect_time_col(df)
df[time_col] = pd.to_datetime(df[time_col], errors="coerce")
if df[time_col].isna().all():
    raise RuntimeError(f"시간열 '{time_col}' 파싱 실패")

df["__date__"] = df[time_col].dt.date
classes = []
for d, sub in df.groupby("__date__", sort=True):
    b = build_boundaries_for_date(d, DELTA_HOURS, SR_HOUR, SS_HOUR)
    cls = assign_time_class_for_day(sub, time_col, b)
    classes.append(cls)
time_class_series = pd.concat(classes).sort_index()

# 기존 time_class 있으면 삭제 후 삽입
if "time_class" in df.columns:
    df = df.drop(columns=["time_class"])
insert_at = df.columns.get_loc(time_col) + 1
df.insert(loc=insert_at, column="time_class", value=time_class_series)
df = df.drop(columns=["__date__"])

df.to_csv(OUT, index=False, encoding="utf-8-sig")
print(f"[SAVE] 새 CSV: {OUT}")
print(f"[INFO] SR={SR_HOUR:02d}:00, SS={SS_HOUR:02d}:00, Δ={DELTA_HOURS}h")