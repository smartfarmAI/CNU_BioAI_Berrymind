#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Tuple, Set

import splitter_min
from stage12_decider import Stage12Decider
from stage34_decider import Stage34Decider


# -----------------------------
# 0) Detector runner (image_sam3_box.py)
# -----------------------------
def run_detector(
    detector_script: Path,
    image_folder: Path,
    output_folder: Path,
    backup_folder: Path,
    boxed_folder: Path,
    prompts: List[str],
    confidence: float,
    pattern: str,
) -> None:
    """
    image_sam3_box.py를 먼저 실행해서 json_dir을 생성/갱신합니다.
    """
    if not detector_script.exists():
        raise FileNotFoundError(f"detector_script not found: {detector_script}")

    cmd = [
        sys.executable, str(detector_script),
        "--image_folder", str(image_folder),
        "--output_folder", str(output_folder),
        "--backup_folder", str(backup_folder),
        "--boxed_folder", str(boxed_folder),
        "--confidence", str(confidence),
        "--pattern", pattern,
        "--prompts",
    ] + prompts

    print(f"[INFO] Running detector: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    print("[INFO] Detector finished.")


# -----------------------------
# I/O helpers
# -----------------------------
def read_json_or_jsonl(path: Path) -> List[dict]:
    suf = path.suffix.lower()
    if suf == ".jsonl":
        items: List[dict] = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    items.append(json.loads(line))
        return items

    if suf == ".json":
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, list) else [obj]

    raise ValueError(f"Unsupported file type: {path}")


def iter_records(input_path: Path) -> Iterable[Tuple[Path, dict]]:
    if input_path.is_file():
        for rec in read_json_or_jsonl(input_path):
            yield input_path, rec
        return

    if input_path.is_dir():
        for p in sorted(input_path.rglob("*.json")):
            for rec in read_json_or_jsonl(p):
                yield p, rec
        for p in sorted(input_path.rglob("*.jsonl")):
            for rec in read_json_or_jsonl(p):
                yield p, rec
        return

    raise FileNotFoundError(f"Input not found: {input_path}")


# -----------------------------
# Business logic helpers
# -----------------------------
def parse_entity_id(record: dict, entity_mode: str = "filename_prefix") -> str:
    if entity_mode == "field":
        if "entity_id" not in record:
            raise ValueError("entity_mode=field 인데 record에 'entity_id'가 없습니다.")
        return str(record["entity_id"])

    filename = record.get("filename", "")
    stem = Path(filename).stem if filename else ""

    if entity_mode == "filename_stem":
        if not stem:
            raise ValueError("record에 filename이 없어 entity_id를 만들 수 없습니다.")
        return stem

    if not stem:
        raise ValueError("record에 filename이 없어 entity_id를 만들 수 없습니다.")
    m = re.match(r"^([A-Za-z0-9]+)[-_]", stem)
    return m.group(1) if m else stem


def detections_to_flags(det: dict) -> Dict[str, int]:
    """
    예시 포맷: {"GREEN FRUIT": 1, "RED FRUIT": 0, "FLOWER": 1}
    """
    def _v(key: str) -> int:
        try:
            return 1 if int(det.get(key, 0)) == 1 else 0
        except Exception:
            return 0

    return {
        "FLOWER": _v("FLOWER"),
        "GREEN FRUIT": _v("GREEN FRUIT"),
        "RED FRUIT": _v("RED FRUIT"),
    }


def normalize_for_presence_check(record: dict) -> dict:
    """
    splitter_min.py / stage34_decider.py가 'key in detections'를 쓰는 구조를 고려:
    0/1 dict -> 값이 1인 라벨만 key로 남기도록 변환
    """
    det = record.get("detections", {}) or {}
    flags = detections_to_flags(det)

    det_present = {}
    for k, v in flags.items():
        if v == 1:
            det_present[k] = 1  # 값은 의미 없음(존재만 하면 됨)

    new_rec = dict(record)
    new_rec["detections"] = det_present
    return new_rec


# -----------------------------
# No-regress helper (옵션)
# -----------------------------
STAGE_RANK = {"S1": 1, "S2": 2, "S3": 3, "S4": 4}


def stage_ge(a: str, b: str) -> bool:
    return STAGE_RANK.get(a, 0) >= STAGE_RANK.get(b, 0)


def max_stage(a: str, b: str) -> str:
    if not a:
        return b
    if not b:
        return a
    return a if STAGE_RANK.get(a, 0) >= STAGE_RANK.get(b, 0) else b


# -----------------------------
# CSV append helpers
# -----------------------------
FIELDNAMES = [
    "source_json",
    "filename",
    "date",
    "time",
    "entity_id",
    "flower",
    "green_fruit",
    "red_fruit",
    "bucket",
    "route_to",
    "stage",
    "first_photo_date",
    "days_since_first",
    "threshold_days",
    "prev_stage",
    "prev_since",
    "reason",
    "override_applied",
    "override_from",
    "override_to",
    "override_reason",
]


def record_key_from_fields(filename: str, date: str, time: str) -> str:
    return f"{filename}|{date}|{time or ''}"


def load_processed_keys(out_csv: Path) -> Set[str]:
    keys: Set[str] = set()
    if not out_csv.exists():
        return keys

    with out_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            fn = r.get("filename", "")
            dt = r.get("date", "")
            tm = r.get("time", "")
            if fn and dt:
                keys.add(record_key_from_fields(fn, dt, tm))
    return keys


# -----------------------------
# Main
# -----------------------------
def main():
    ap = argparse.ArgumentParser()

    # (A) detector 관련 옵션
    ap.add_argument("--skip_detector", action="store_true", help="SAM3 detector(image_sam3_box.py) 실행을 생략")
    ap.add_argument("--detector_script", default="./image_sam3_box.py", help="SAM3 detector 스크립트 경로")
    ap.add_argument("--detector_image_folder", default="./images", help="이미지 입력 폴더")
    ap.add_argument("--detector_output_folder", default="./json_dir", help="detector가 JSON을 저장할 폴더")
    ap.add_argument("--detector_backup_folder", default="./processed_images", help="원본 이미지 백업 폴더(이동)")
    ap.add_argument("--detector_boxed_folder", default="./boxed_images", help="박스 그린 이미지 저장 폴더")
    ap.add_argument("--detector_prompts", nargs="+", default=["GREEN FRUIT", "RED FRUIT", "FLOWER"])
    ap.add_argument("--detector_confidence", type=float, default=0.5)
    ap.add_argument("--detector_pattern", default="*.png")

    # (B) stage 파이프라인 옵션
    ap.add_argument(
        "--input",
        default=None,
        help="stage 입력(json/jsonl 또는 폴더). 지정 안 하면 detector_output_folder를 사용",
    )
    ap.add_argument("--out_csv", default="out.csv", help="출력 CSV (append)")
    ap.add_argument(
        "--entity_mode",
        choices=["filename_prefix", "filename_stem", "field"],
        default="filename_prefix",
        help="entity_id 생성 규칙",
    )
    ap.add_argument(
        "--disable_monotonic",
        action="store_true",
        help="이번 실행에서 stage 역행 방지(최종 안전장치) 끄기",
    )
    args = ap.parse_args()

    detector_script = Path(args.detector_script)
    image_folder = Path(args.detector_image_folder)
    detector_out_folder = Path(args.detector_output_folder)
    backup_folder = Path(args.detector_backup_folder)
    boxed_folder = Path(args.detector_boxed_folder)

    # 1) 먼저 detector 실행
    if not args.skip_detector:
        run_detector(
            detector_script=detector_script,
            image_folder=image_folder,
            output_folder=detector_out_folder,
            backup_folder=backup_folder,
            boxed_folder=boxed_folder,
            prompts=args.detector_prompts,
            confidence=args.detector_confidence,
            pattern=args.detector_pattern,
        )

    # 2) stage 입력은 기본적으로 detector_output_folder 사용
    input_path = Path(args.input) if args.input is not None else detector_out_folder
    out_csv = Path(args.out_csv)

    dec12 = Stage12Decider()
    dec34 = Stage34Decider()

    processed_keys = load_processed_keys(out_csv)
    best_stage_seen: Dict[str, str] = {}

    need_header = (not out_csv.exists()) or (out_csv.stat().st_size == 0)
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    added = 0
    skipped = 0

    with out_csv.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if need_header:
            w.writeheader()

        for src_path, rec in iter_records(input_path):
            if "filename" not in rec or "date" not in rec:
                continue

            filename = rec.get("filename", "")
            date_str = rec.get("date", "")
            time_str = rec.get("time", "")

            k = record_key_from_fields(filename, date_str, time_str)
            if k in processed_keys:
                skipped += 1
                continue
            processed_keys.add(k)

            entity_id = parse_entity_id(rec, args.entity_mode)

            det = rec.get("detections", {}) or {}
            flags = detections_to_flags(det)
            rec_presence = normalize_for_presence_check(rec)

            bucket, _payload = splitter_min.split_for_stage12_or_34(rec_presence)

            row = {
                "source_json": str(src_path),
                "filename": filename,
                "date": date_str,
                "time": time_str,
                "entity_id": entity_id,
                "flower": flags["FLOWER"],
                "green_fruit": flags["GREEN FRUIT"],
                "red_fruit": flags["RED FRUIT"],
                "bucket": bucket,
                "route_to": "",
                "stage": "",
                "first_photo_date": "",
                "days_since_first": "",
                "threshold_days": "",
                "prev_stage": "",
                "prev_since": "",
                "reason": "",
                "override_applied": 0,
                "override_from": "",
                "override_to": "",
                "override_reason": "",
            }

            # 한번이라도 stage34 이력이 있으면 stage12로 “라우팅 역행” 금지
            has_stage34_history = entity_id in getattr(dec34, "state", {})
            forced_record_for_34 = None
            if bucket == "stage12" and has_stage34_history:
                rec_for_34 = dict(rec_presence)
                rec_for_34["detections"] = {}  # evidence 없음
                forced_record_for_34 = rec_for_34
                bucket = "stage34_forced"
                row["bucket"] = bucket

            decided_stage = ""

            if bucket == "stage12":
                r12 = dec12.decide(entity_id, date_str)
                row["route_to"] = "stage12"
                row["stage"] = r12.stage
                row["first_photo_date"] = r12.first_photo_date
                row["days_since_first"] = r12.days_since_first
                row["threshold_days"] = r12.threshold_days
                decided_stage = r12.stage
            else:
                r34 = dec34.decide(entity_id, forced_record_for_34 or rec_presence)
                row["route_to"] = bucket
                row["stage"] = r34.stage if r34.stage is not None else ""
                row["prev_stage"] = r34.prev_stage if r34.prev_stage is not None else ""
                row["prev_since"] = r34.prev_since if r34.prev_since is not None else ""
                row["reason"] = r34.reason if bucket != "stage34_forced" else ("forced_to_stage34; " + r34.reason)
                decided_stage = row["stage"]

            # 최종 안전장치(이번 실행 내) 역행 방지(선택)
            if not args.disable_monotonic and decided_stage in STAGE_RANK:
                prev_best = best_stage_seen.get(entity_id, "")
                new_best = max_stage(prev_best, decided_stage)

                if prev_best and not stage_ge(decided_stage, prev_best):
                    row["override_applied"] = 1
                    row["override_from"] = decided_stage
                    row["override_to"] = prev_best
                    row["override_reason"] = "monotonic_no_regress(best_stage_seen_this_run)"
                    row["stage"] = prev_best
                    decided_stage = prev_best

                best_stage_seen[entity_id] = new_best

            w.writerow(row)
            added += 1

    print(f"[OK] append 완료: +{added} rows, skipped={skipped} (이미 처리된 레코드)")
    print(f"[OK] out_csv: {out_csv.resolve()}")


if __name__ == "__main__":
    main()
