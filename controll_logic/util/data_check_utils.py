import json
from collections import Counter

def extract_condition_names(filepath: str):
    with open(filepath, "r", encoding="utf-8") as f:
        rules = json.load(f)

    names = set()

    def collect_conditions(conds):
        # all / any 리스트 처리
        for key in ("all", "any"):
            if key in conds:
                for cond in conds[key]:
                    if "name" in cond:
                        names.add(cond["name"])
                    # nested 조건도 탐색 가능
                    collect_conditions(cond)

    for rule in rules:
        if "conditions" in rule:
            collect_conditions(rule["conditions"])

    return names

def check_rule_name_duplicates(filepath: str):
    with open(filepath, "r", encoding="utf-8") as f:
        rules = json.load(f)

    # 모든 name 값 수집
    names = [rule.get("name") for rule in rules if "name" in rule]

    # Counter로 빈도 계산
    counter = Counter(names)

    # 중복만 뽑기
    duplicates = {name: count for name, count in counter.items() if count > 1}

    if duplicates:
        print("⚠️ 중복된 이름이 있습니다:")
        for name, count in duplicates.items():
            print(f"  - {name} (총 {count}번)")
    else:
        print("✅ 중복된 이름 없음")

if __name__ == "__main__":
    filepath = "rule_engine/rules.json"
    condition_names = extract_condition_names(filepath)
    print("변수 목록:", condition_names)
    print("총 개수:", len(condition_names))

    check_rule_name_duplicates(filepath)
