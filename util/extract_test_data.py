import sys
from datetime import datetime, timedelta, time
import pandas as pd

LAT, LON = 35.8, 127.1  # 완주군 이서면

# 실제 모듈 경로로 교체하세요.
from SRSSCalc import SunriseCalculator

def band_windows(calc, date_str: str):
    """해당 날짜의 t1..t8 반열림 구간 {band: (start, end)} 반환"""
    d = datetime.strptime(date_str, "%Y-%m-%d").date()
    sr_str, ss_str = calc.calculate_sunrise_sunset(d.strftime("%Y%m%d"))
    SR = datetime.strptime(f"{d} {sr_str}", "%Y-%m-%d %H:%M")
    SS = datetime.strptime(f"{d} {ss_str}", "%Y-%m-%d %H:%M")
    NOON = datetime.combine(d, time(12, 0))
    DAY0 = datetime.combine(d, time(0, 0))
    DAY1 = DAY0 + timedelta(days=1)  # 다음날 00:00

    SR_m3, SR_p3 = SR - timedelta(hours=3), SR + timedelta(hours=3)
    SS_m3, SS_p3 = SS - timedelta(hours=3), SS + timedelta(hours=3)

    return {
        1: (SR, SR_p3),
        2: (SR_p3, NOON),
        3: (NOON, SS_m3),
        4: (SS_m3, SS),
        5: (SS, SS_p3),
        6: (min(SS_p3, DAY1), DAY1),   # SS+3h ~ 24:00
        7: (DAY0, max(SR_m3, DAY0)),   # 00:00 ~ SR-3h
        8: (max(SR_m3, DAY0), SR),     # SR-3h ~ SR
    }

def extract_all_bands(in_csv: str, out_csv: str, date_str: str, step_min: int):
    df = pd.read_csv(in_csv)
    if "저장시간" not in df.columns:
        raise ValueError("'저장시간' 컬럼이 없습니다.")
    df["저장시간"] = pd.to_datetime(df["저장시간"])

    calc = SunriseCalculator(LAT, LON)
    windows = band_windows(calc, date_str)

    parts = []
    for band, (start, end) in windows.items():
        mask = (df["저장시간"] >= start) & (df["저장시간"] < end)
        sub = df.loc[mask].copy()
        # 밴드 시작 기준 n분 간격에 맞는 시점만 선택
        sub = sub[(sub["저장시간"] - start) % pd.Timedelta(minutes=step_min) == pd.Timedelta(0)]
        if not sub.empty:
            sub["timeband"] = band
            parts.append(sub)

    out = pd.concat(parts, ignore_index=True) if parts else df.iloc[0:0].copy()
    out.sort_values(["저장시간", "timeband"], inplace=True)
    out.to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(f"saved: {out_csv} | rows={len(out)} | date={date_str} | step={step_min}min")

if __name__ == "__main__":
    # 사용법: python extract_test_data.py 첨단온실_2구역_new.csv test_sample.csv 2024-05-28 30
    if len(sys.argv) < 5:
        print("Usage: python extract_test_data.py <in.csv> <out.csv> <YYYY-MM-DD> <step_min>")
        sys.exit(1)
    in_csv, out_csv, dstr, step_str = sys.argv[1:5]
    extract_all_bands(in_csv, out_csv, dstr, int(step_str))
