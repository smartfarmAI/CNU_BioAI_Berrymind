from __future__ import annotations
import pandas as pd
from typing import Iterable, Mapping, Any, Optional, List, Tuple, Dict, Callable, Optional
import numpy as np

def check_continuous_minutes(df, timestamp_col='timestamp'):
    # 시간 컬럼 정렬
    df_sorted = df.sort_values(timestamp_col).copy()
    
    # timestamp 컬럼을 datetime으로 변환 보장
    df_sorted[timestamp_col] = pd.to_datetime(df_sorted[timestamp_col])
    
    # 첫 번째와 마지막 시간
    start_time = df_sorted[timestamp_col].iloc[0]
    end_time = df_sorted[timestamp_col].iloc[-1]
    
    # 예상되는 총 시간 수 (1분 단위)
    expected_minutes = int((end_time - start_time).total_seconds() / 60) + 1
    actual_records = len(df_sorted)
    
    print(f"시작 시간: {start_time}")
    print(f"종료 시간: {end_time}")
    print(f"예상 레코드 수: {expected_minutes:,}")
    print(f"실제 레코드 수: {actual_records:,}")
    
    if expected_minutes == actual_records:
        print("✅ 1분 단위로 연속적인 데이터입니다!")
        return True
    else:
        print(f"❌ {expected_minutes - actual_records:,}개의 레코드가 누락되었습니다.")
        return False

def find_missing_timestamps(df, timestamp_col='timestamp'):
    # 데이터가 비어있으면 바로 반환
    if df is None or df.empty:
        print("⚠️ 입력 데이터프레임이 비어 있습니다.")
        return ["EMPTY_DF"]
    
    df_sorted = df.sort_values(timestamp_col).copy()
    
    # timestamp 컬럼을 datetime으로 변환 보장
    df_sorted[timestamp_col] = pd.to_datetime(df_sorted[timestamp_col])
    
    # 완전한 1분 단위 시간 범위 생성
    start_time = df_sorted[timestamp_col].iloc[0]
    end_time = df_sorted[timestamp_col].iloc[-1]
    
    complete_range = pd.date_range(
        start=start_time, 
        end=end_time, 
        freq='1T'  # 1분 단위
    )
    
    # 실제 데이터의 타임스탬프 집합
    actual_timestamps = set(df_sorted[timestamp_col])
    expected_timestamps = set(complete_range)
    
    # 누락된 타임스탬프 찾기
    missing_timestamps = expected_timestamps - actual_timestamps
    
    if missing_timestamps:
        print(f"❌ {len(missing_timestamps):,}개의 시간대가 누락되었습니다:")
        
        # 처음 10개만 출력
        sorted_missing = sorted(missing_timestamps)[:10]
        for ts in sorted_missing:
            print(f"  - {ts}")
        
        if len(missing_timestamps) > 10:
            print(f"  ... 그 외 {len(missing_timestamps)-10}개 더")
            
        return sorted(missing_timestamps)
    else:
        print("✅ 모든 1분 단위 데이터가 존재합니다!")
        return []

def filter_by_interval(df, timestamp_col='timestamp', interval_minutes=5, start_time=None):
    """
    지정된 시작 시간을 기준으로 지정된 분 간격의 데이터만 필터링
    
    Args:
        df: DataFrame
        timestamp_col: timestamp 컬럼명
        interval_minutes: 간격(분), 기본값 5분
        start_time: 기준 시작 시간 (None이면 데이터의 첫 번째 시간 사용)
    
    Returns:
        필터링된 DataFrame
    """
    df_copy = df.copy()
    
    # timestamp 컬럼을 datetime으로 변환 보장
    df_copy[timestamp_col] = pd.to_datetime(df_copy[timestamp_col])
    
    # 시작 시간 설정
    df_sorted = df_copy.sort_values(timestamp_col)
    if start_time is None:
        start_time = df_sorted[timestamp_col].iloc[0]
    else:
        start_time = pd.to_datetime(start_time)
    
    print(f"🕐 시작 시간: {start_time}")
    print(f"📏 필터링 간격: {interval_minutes}분")
    
    # 시작 시간 이후의 데이터만 필터링 (핵심 버그 수정!)
    df_after_start = df_sorted[df_sorted[timestamp_col] >= start_time].copy()
    
    # 시작 시간으로부터 경과된 분 계산 (이제 모두 양수)
    df_after_start['minutes_from_start'] = (df_after_start[timestamp_col] - start_time).dt.total_seconds() / 60
    
    # 지정된 간격의 배수인 행만 필터링 (허용 오차 추가)
    tolerance = 0.01  # 0.01분 = 0.6초 허용 오차
    df_after_start['remainder'] = df_after_start['minutes_from_start'] % interval_minutes
    df_after_start['is_interval'] = (df_after_start['remainder'] < tolerance) | (df_after_start['remainder'] > (interval_minutes - tolerance))
    filtered_df = df_after_start[df_after_start['is_interval']].copy()
    
    # 임시 컬럼들 제거
    filtered_df = filtered_df.drop(['minutes_from_start', 'remainder', 'is_interval'], axis=1)
    
    print(f"📊 결과:")
    print(f"  원본 데이터: {len(df_copy):,}개")
    print(f"  필터링 후: {len(filtered_df):,}개")
    print(f"  필터링 비율: {len(filtered_df)/len(df_copy)*100:.1f}%")
    
    # 처음 몇 개 타임스탬프 예시 출력
    print(f"📅 필터링된 타임스탬프 예시 (처음 5개):")
    for i, ts in enumerate(filtered_df[timestamp_col].head(5)):
        print(f"  {i+1}. {ts}")
    
    return filtered_df

def apply_boundary_clipping(df, boundary_rule, columns):
    """
    지정된 컬럼들을 바운더리 룰에 따라 클리핑
    
    Args:
        df: 원본 DataFrame
        boundary_rule: {'min': float, 'max': float} 클리핑 범위
        columns: 클리핑할 컬럼 리스트
        timestamp_col: timestamp 컬럼명 (기본값: 'timestamp')
    
    Returns:
        클리핑된 DataFrame (원본은 변경되지 않음)
        
    Example:
        >>> boundary_rule = {'min': -30, 'max': 50}
        >>> columns = ['temp1', 'temp2']
        >>> clipped_df = apply_boundary_clipping(df, boundary_rule, columns)
    """
    # 원본 보호를 위한 딥카피
    result_df = df.copy()
    
    # 바운더리 룰에서 min, max 값 추출
    min_val = boundary_rule.get('min')
    max_val = boundary_rule.get('max')
    
    # 각 컬럼에 대해 클리핑 적용
    for column in columns:
        if column not in result_df.columns:
            raise KeyError(f"컬럼 '{column}'이 DataFrame에 존재하지 않습니다.")
        
        # pandas의 clip 함수 사용하여 클리핑
        result_df[column] = result_df[column].clip(lower=min_val, upper=max_val)
    
    return result_df

def present(df: pd.DataFrame, cols: Optional[Iterable[str]]) -> List[str]:
    """df에 실제 존재하는 컬럼만 골라서 반환."""
    return [c for c in (cols or []) if c in df.columns]


def apply_value_map(
    df: pd.DataFrame,
    value_map: Mapping[str, Mapping[Any, Any]],
    on_unexpected: str = "error",   # "error" | "warn" | "keep" | "fill" | "drop"
    fill_unmapped: Any = 0,         # on_unexpected="fill"일 때 사용
    out_dtype: Optional[str] = "float32",
) -> pd.DataFrame:
    """열별 값 매핑(예: 201→1). 예상 밖 값 처리 전략을 선택 가능."""
    out = df.copy()
    for col, mapping in (value_map or {}).items():
        if col not in out.columns:
            continue
        s = out[col]
        unexpected = set(pd.Series(s).dropna().unique()) - set(mapping.keys())
        if unexpected:
            if on_unexpected == "error":
                raise AssertionError(f"{col} unexpected values: {unexpected}")
            elif on_unexpected == "warn":
                print(f"[WARN] {col} unexpected values: {unexpected} (kept)")
            elif on_unexpected == "drop":
                mask = ~pd.Series(s).isin(mapping.keys())
                out.loc[mask, col] = pd.NA
            elif on_unexpected == "fill":
                pass  # 아래 fill 단계에서 처리
            elif on_unexpected == "keep":
                pass

        mapped = pd.Series(s).map(mapping)
        if on_unexpected == "fill":
            mapped = mapped.fillna(fill_unmapped)
        out[col] = mapped if out_dtype is None else mapped.astype(out_dtype)
    return out


def flatten_columns(df: pd.DataFrame, sep: str = "_") -> pd.DataFrame:
    """GroupBy agg 뒤 MultiIndex 컬럼을 평탄화."""
    out = df.copy()
    if isinstance(out.columns, pd.MultiIndex):
        out.columns = [sep.join([str(x) for x in tup if x != ""]) for tup in out.columns]
    return out


def impute_minutes_with_daily_fallback(
    df: pd.DataFrame,
    cols,
    max_gap_min: int = 2,                     # 분 단위 한계(±K분)
    strategy: str = "ffill_then_bfill",       # "ffill" | "bfill" | "ffill_then_bfill"
    day_fallback_days: tuple[int, ...] = (1,),# (1,)이면 전일, (1,7)이면 전일→7일전 순으로
    day_tolerance_min: int = 0,               # 전일 같은 시각에서 ±허용 분(0이면 정확히 같은 분만)
    by=None,                                  # 예: "device_id"
    time_col: str = "time",
) -> pd.DataFrame:
    """
    1) 시간 간격(분) 기준으로 ffill/bfill 제한 채움
    2) 남은 NaN은 day_fallback_days에 따라 전일/7일전 '같은 시각' 값으로 채움(±tolerance 허용)
    """
    out = df.copy()
    cols = [c for c in (cols or []) if c in out.columns]
    if not cols: 
        return out

    tol = pd.Timedelta(minutes=day_tolerance_min)

    def _fill(group: pd.DataFrame) -> pd.DataFrame:
        g = group.sort_values(time_col).copy()
        t = pd.to_datetime(g[time_col], errors="coerce")
        idx = g.index

        for c in cols:
            s = g[c]
            s_out = s.copy()

            # ---- 1) 분 기준 ffill/bfill (갭 가드) ----
            # ffill
            if strategy in ("ffill", "ffill_then_bfill"):
                prev_obs_time = t.where(s.notna()).ffill()
                gap_min = (t - prev_obs_time).dt.total_seconds() / 60.0
                s_ff = s.ffill()
                s_out = s_ff.where(gap_min <= max_gap_min, other=pd.NA)
            # bfill
            if strategy in ("bfill", "ffill_then_bfill"):
                next_obs_time = t.where(s.notna()).bfill()
                gap_min_b = (next_obs_time - t).dt.total_seconds() / 60.0
                s_bf = s.bfill()
                s_bf_limited = s_bf.where(gap_min_b <= max_gap_min, other=pd.NA)
                s_out = s_out.fillna(s_bf_limited)

            # ---- 2) 전일/여러 일 전 같은 시각 fallback ----
            if day_fallback_days:
                # 관측치 테이블(결측 제외)
                base = pd.DataFrame({"time": t, "val": s}).dropna().sort_values("time")
                for d in day_fallback_days:
                    if base.empty:
                        break
                    target = pd.DataFrame({"orig_idx": idx, "time": t - pd.Timedelta(days=d)}).sort_values("time")
                    # 같은 시각(±tolerance) 매칭
                    matched = pd.merge_asof(
                        target, base, on="time",
                        direction="nearest",
                        tolerance=tol
                    )
                    # 원래 순서로 복원하여 후보 시리즈 추출
                    cand = matched.set_index("orig_idx").reindex(idx)["val"]
                    # 아직 NaN인 곳만 채움
                    s_out = s_out.where(~s_out.isna(), cand)

            g[c] = s_out
        return g

    if by:
        out = out.groupby(by, group_keys=False).apply(_fill)
    else:
        out = _fill(out)
    return out


def bounds_check(df: pd.DataFrame, bounds: dict) -> pd.DataFrame:
    """
    YAML의 pre.bounds를 기준으로 컬럼 존재/범위 위반 개수를 리포트만 함(데이터 변경 X).
    반환: 컬럼별 요약 테이블(DataFrame)
    """
    rows = []
    for col, lim in (bounds or {}).items():
        present = col in df.columns
        if not present:
            rows.append({
                "col": col, "present": False, "n": 0,
                "min": lim.get("min", None), "max": lim.get("max", None),
                "below_min": None, "above_max": None,
                "violations": None, "nan_count": None,
            })
            continue

        s = pd.to_numeric(df[col], errors="coerce")
        lo = lim.get("min", None); hi = lim.get("max", None)
        below = (s < lo).sum() if lo is not None else 0
        above = (s > hi).sum() if hi is not None else 0
        rows.append({
            "col": col, "present": True, "n": int(s.shape[0]),
            "min": lo, "max": hi,
            "below_min": int(below), "above_max": int(above),
            "violations": int(below + above),
            "nan_count": int(s.isna().sum()),
        })
    out = pd.DataFrame(rows)
    # 보기 좋게 정렬
    if not out.empty and "violations" in out.columns:
        out = out.sort_values(["present","violations","nan_count"], ascending=[False, False, False])
    return out


def apply_bounds(df, bounds: dict, mode="nan"):
    out = df.copy()
    for col, lim in (bounds or {}).items():
        if col not in out.columns: 
            continue
        s = out[col]
        if mode == "clip":                       # 경계로 자르기
            out[col] = s.clip(lim.get("min", None), lim.get("max", None))
        else:                                    # "nan": 범위 밖 → NaN
            mask = False
            if "min" in lim: mask = (s < lim["min"])
            if "max" in lim: mask = mask | (s > lim["max"])
            out.loc[mask, col] = pd.NA
    return out


def assert_no_na(df, name="df"):
    s = df.isna().sum()
    assert (s==0).all(), f"[{name}] NaNs: {s[s>0].to_dict()}"


def assert_bounds(df, bounds: dict):
    for col, lim in bounds.items():
        if col in df.columns:
            s = pd.to_numeric(df[col], errors="coerce").dropna()
            lo = lim.get("min", -np.inf); hi = lim.get("max", np.inf)
            assert s.min() >= lo and s.max() <= hi, f"{col} not clipped properly"
    print(f"[{bounds.keys()}] bounds check passed")

"""
y_interval_minutes = y 데이터를 몇분 간격으로 모을지 10분
horizon_min = 지금 시점으로부터 몇 분 후를 예측하는지 35분
window_min = X의 윈도우 사이즈 10분
"""
def make_X_y_data(
    df: pd.DataFrame,
    horizon_min: int,
    window_min: int,
    y_interval_minutes: int = 10,
    timestamp_col: str = "time",
) -> Tuple[Dict[pd.Timestamp, pd.DataFrame], pd.DataFrame]:
    """
    반환:
      - X_windows: {y_time: X(해당 y_time에 대응하는 1분 간격 window_min개 DataFrame)}
      - y_df: 유효한 y 시점들만 모은 DataFrame (y 후보 중 x가 유효한 것만 남김)

    규칙:
      - y 시점: df에서 실제로 존재하며 interval에 맞는 시각만 사용
      - x 윈도우: [T - horizon_min - (window_min - 1), ..., T - horizon_min] (총 window_min개, 1분 간격)
      - 윈도우가 '정확히 window_min개' + '모두 1분 간격' 이 아니면 해당 y는 폐기
    """
    df = df.copy()
    df[timestamp_col] = pd.to_datetime(df[timestamp_col])
    df = df.drop_duplicates(subset=[timestamp_col]).set_index(timestamp_col).sort_index()

    # 1분 간격으로 리샘플 (누락은 NaN으로 채움)
    df = df.asfreq("1min")

    # y 후보: interval에 맞는 시각 중 실제 값 있는 것만
    y_cands = df.iloc[::y_interval_minutes].dropna(how="all")

    X_windows, valid_y = {}, []

    for T in y_cands.index:
        x_start = T - pd.Timedelta(minutes=horizon_min + (window_min - 1))
        x_end   = T - pd.Timedelta(minutes=horizon_min)

        sub = df.loc[x_start:x_end]

        # 길이, 결측 체크만 하면 됨
        if len(sub) == window_min and not sub.isna().any().any():
            X_windows[T] = sub.reset_index()
            valid_y.append(T)

    y_df = df.loc[valid_y].reset_index()
    return X_windows, y_df
