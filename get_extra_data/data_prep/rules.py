import pandas as pd
from .registry import register
from .utils import *

@register("r0_basic")
def r0(df, cfg):
    print("r0_basic : 기본 집계 (no pre)")
    df = df.copy()
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    # 5분 버킷
    df["set_id"] = df["time"].dt.floor(cfg.get("window", "5min"))

    # (0) - 1 RAW bounds 리포트만 (데이터 변경 X)
    pre = cfg.get("pre") or {}
    report = bounds_check(df, pre.get("bounds", {}))
    print("\n[pre.bounds report - BEFORE]")
    print(report.to_string(index=False))

    # (1) 값 변환 (예: 201 -> 1)
    df = apply_value_map(
        df,
        cfg.get("value_map", {}),
        on_unexpected=cfg.get("on_unexpected", "error"),
        fill_unmapped=cfg.get("fill_unmapped", 0),
        out_dtype="float32",
    )

    # (2) 집계
    mean_cols = present(df, cfg.get("x_mean_cols"))
    sum_cols  = present(df, cfg.get("x_sum_cols"))
    agg = {**{c: "mean" for c in mean_cols}, **{c: "sum" for c in sum_cols}}

    out = df.groupby("set_id", as_index=False).agg(agg)
    out = flatten_columns(out)
    out = out.rename(columns={"set_id": "time"})

    return out

@register("r1_impute_minutes_with_daily_fallback")
def r1(df, cfg):
    print("r1_impute_minutes_with_daily_fallback start")
    df = df.copy()
    df["time"] = pd.to_datetime(df["time"], errors="coerce")

    win = cfg.get("window_size", 5)
    df["set_id"] = (df.index // win).astype("int64")
    
    # (0) - 1 RAW bounds 리포트만 (데이터 변경 X)
    pre = cfg.get("pre") or {}
    report = bounds_check(df, pre.get("bounds", {}))
    print("\n[pre.bounds report - BEFORE]")
    print(report.to_string(index=False))

    # (0) - 2 클리핑 적용
    df = apply_bounds(df, pre.get("bounds", {}), mode=pre.get("bounds_mode", "nan"))
    imp = (cfg.get("pre") or {}).get("impute", {}) or {}
    fill_cols = list((cfg.get("pre") or {}).get("bounds", {}).keys())  # 우선 bounds의 키만
    df = df.sort_values("time")
    
    df = impute_minutes_with_daily_fallback(
        df, fill_cols,
        max_gap_min=imp.get("limit", 2),                 # 분 단위
        strategy=imp.get("strategy", "ffill_then_bfill"),
        day_fallback_days=tuple(imp.get("day_fallback_days", [1])),  # 전일 fallback
        day_tolerance_min=imp.get("day_tolerance_min", 0),           # 전일 시각 일치 허용 오차(분)
        by=imp.get("by", None),
        time_col=imp.get("order_col", "time"),
    )

    # (0) - 3 리포트(적용 후)
    report2 = bounds_check(df, pre.get("bounds", {}))
    print("\n[pre.bounds report - AFTER]")
    print(report2.to_string(index=False))

    # (0) - 4 경계 검증(결측 제외하고 min/max만 체크)
    assert_bounds(df, pre.get("bounds", {}))

    # (1) 값 변환 (예: 201 -> 1)
    df = apply_value_map(
        df,
        cfg.get("value_map", {}),
        on_unexpected=cfg.get("on_unexpected", "error"),
        fill_unmapped=cfg.get("fill_unmapped", 0),
        out_dtype="float32",
    )

    # (2) 집계
    mean_cols = present(df, cfg.get("x_mean_cols"))
    sum_cols  = present(df, cfg.get("x_sum_cols"))
    agg = {**{c: "mean" for c in mean_cols}, **{c: "sum" for c in sum_cols}}

    out = df.groupby("set_id", as_index=False).agg(agg)
    out = flatten_columns(out)
    # out = out.rename(columns={"set_id": "time"})

    assert_no_na(out, name="agg_out")
    return out

@register("r2_for_inference")
def r1(df, cfg):
    print("r2_for_inference")
    df = df.copy()
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    
    # (0) - 클리핑 적용
    pre = cfg.get("pre") or {}
    df = apply_bounds(df, pre.get("bounds", {}), mode=pre.get("bounds_mode", "nan"))
    df = df.sort_values("time")

    # (1) 값 변환 (예: 201 -> 1)
    df = apply_value_map(
        df,
        cfg.get("value_map", {}),
        on_unexpected=cfg.get("on_unexpected", "error"),
        fill_unmapped=cfg.get("fill_unmapped", 0),
        out_dtype="float32",
    )

    # (2) 집계
    mean_cols = present(df, cfg.get("x_mean_cols"))
    sum_cols  = present(df, cfg.get("x_sum_cols"))
    agg = {**{c: "mean" for c in mean_cols}, **{c: "sum" for c in sum_cols}}

    # DataFrame 전체 집계 → 결과는 1행
    out = df.agg(agg).to_frame().T.reset_index(drop=True)

    assert_no_na(out, name="agg_out")
    return out
