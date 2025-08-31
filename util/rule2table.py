import json
from pathlib import Path
from typing import Any, Dict, List
import pandas as pd

# ---- 조건 파싱 유틸 ----
def _find_cond(conds: Dict[str, Any], name: str):
    """conditions = {'all':[...]} 구조에서 특정 name 조건(여러 개면 리스트) 반환"""
    if not conds:
        return []
    items = []
    for c in conds.get("all", []):
        if "all" in c or "any" in c:
            items.extend(_find_cond(c, name))
        else:
            if c.get("name") == name:
                items.append(c)
    return items

def _first_val(conds: Dict[str, Any], name: str, default=None):
    xs = _find_cond(conds, name)
    return xs[0] if xs else default

def _fmt_one(c: Dict[str, Any]) -> str:
    if not c: return ""
    # e.g. {"name":"indoor_CO2","operator":"less_than_or_equal_to","value":300}
    op = c.get("operator", "")
    # 가독성 치환
    op_map = {
        "less_than": "<", "less_than_or_equal_to": "≤",
        "greater_than": ">", "greater_than_or_equal_to": "≥",
        "equal_to": "=", "not_equal_to": "≠",
    }
    op_sym = op_map.get(op, op)
    val = c.get("value")
    # JSON에 true/false가 있으면 1/0처럼 보이도록
    if isinstance(val, bool):
        val = 1 if val else 0
    return f'{c.get("name")} {op_sym} {val}'

def _conditions_expr(conds: Dict[str, Any]) -> str:
    # 핵심 신호들 우선 정리(있으면 맨 앞에)
    keys_order = ["time_band", "indoor_CO2", "solar_radiation", "rain"]
    picked = []
    seen = set()
    for k in keys_order:
        c = _first_val(conds, k)
        if c:
            picked.append(_fmt_one(c))
            seen.add(id(c))
    # 나머지 조건도 이어붙이기
    rest = []
    for c in conds.get("all", []):
        if isinstance(c, dict) and ("name" in c) and (id(c) not in seen):
            rest.append(_fmt_one(c))
    parts = [x for x in (picked + rest) if x]
    return " AND ".join(parts)

def _action_expr(act: Dict[str, Any]) -> str:
    # {"actuator":"CO2","state":"ON","duration_sec":0,"pause_sec":0}
    a = act.get("actuator","")
    s = act.get("state","")
    dur = act.get("duration_sec",0)
    pause = act.get("pause_sec",0)
    extra = []
    if dur: extra.append(f"dur={dur}s")
    if pause: extra.append(f"pause={pause}s")
    extra_str = f" ({', '.join(extra)})" if extra else ""
    return f"{a}:{s}{extra_str}"

def rules_to_table(rules: List[Dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for r in rules:
        conds = r.get("conditions", {})
        acts  = r.get("actions", [])
        # 액션 여러 개면 모두 행으로 풀기
        for a in acts:
            params = a.get("params", {})
            # 타임밴드 추출(없으면 None)
            tb = _first_val(conds, "time_band")
            tb_val = tb.get("value") if tb else None
            if isinstance(tb_val, bool):  # 혹시 불리언이면 숫자처럼
                tb_val = 1 if tb_val else 0

            rows.append({
                "time_band": tb_val,
                "rule_name": r.get("name",""),
                "priority":  r.get("priority", 0),
                "conditions": _conditions_expr(conds),
                "action": _action_expr(params),
            })
    df = pd.DataFrame(rows)
    # 보기 좋게 정렬: time_band, actuator(action 앞부분), priority desc
    def _actuator(x: str) -> str:
        return (x.split(":")[0] if isinstance(x, str) and ":" in x else x) or ""
    if not df.empty:
        df["actuator"] = df["action"].map(_actuator)
        df = df.sort_values(by=["time_band","actuator","priority"], ascending=[True, True, False])
        # 컬럼 순서 재배치
        df = df[["time_band","actuator","rule_name","priority","conditions","action"]]
    return df


def load_rules_from_rules_conf() -> List[Dict[str, Any]]:
    """rule_engine/rules_conf 디렉토리 밑의 모든 JSON을 읽어서 합친다"""
    base = Path(__file__).resolve().parent       # util/
    rules_dir = base.parent / "rule_engine" / "rules_conf"
    rules = []
    for fp in sorted(rules_dir.glob("*.json")):
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
            if isinstance(data, list):
                rules.extend(data)
        except Exception as e:
            print(f"[WARN] {fp.name} 불러오기 실패: {e}")
    return rules
def _iter_rule_json_files() -> List[Path]:
    """../rule_engine/rules_conf/*.json 경로 목록 반환"""
    base = Path(__file__).resolve().parent            # util/
    rules_dir = base.parent / "rule_engine" / "rules_conf"
    return sorted(rules_dir.glob("*.json"))

def _load_rules_file(fp: Path) -> List[Dict[str, Any]]:
    try:
        data = json.loads(fp.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"[WARN] {fp.name} 불러오기 실패: {e}")
        return []

# if __name__ == "__main__":
#     rules = load_rules_from_rules_conf()
#     df = rules_to_table(rules)
#     df.to_markdown("rules_table.md", index=False)
    
if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parent / "outputs"
    out_dir.mkdir(exist_ok=True)

    files = _iter_rule_json_files()
    if not files:
        raise SystemExit("rules_conf에 JSON 파일이 없습니다.")

    total_rows = 0
    for fp in files:
        rules = _load_rules_file(fp)
        df = rules_to_table(rules)

        # 파일별 마크다운/CSV 이름
        stem = fp.stem  # 예: co2_rules.json -> co2_rules
        md_path  = out_dir / f"{stem}_rules.md"
        csv_path = out_dir / f"{stem}_rules.csv"

        # 표 저장
        df.to_csv(csv_path, index=False)
        try:
            df.to_markdown(md_path, index=False)   # tabulate 필요
        except Exception:
            # tabulate 미설치면 markdown 건너뜀
            pass

        # (옵션) 타임밴드 x 구동기 매트릭스도 만들고 싶다면 주석 해제
        # mat = rules_to_matrix(df)
        # mat_md_path  = out_dir / f"{stem}_matrix.md"
        # mat_csv_path = out_dir / f"{stem}_matrix.csv"
        # mat.to_csv(mat_csv_path)
        # try:
        #     mat.to_markdown(mat_md_path)
        # except Exception:
        #     pass

        print(f"✓ {fp.name} -> {csv_path.name}" + (f", {md_path.name}" if md_path.exists() else ""))
        total_rows += len(df)

    print(f"\n완료: {len(files)}개 파일, 총 {total_rows}개 행 정리")