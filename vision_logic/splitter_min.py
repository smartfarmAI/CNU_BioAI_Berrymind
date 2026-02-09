def to_flag(record, key: str) -> int:
    det = record.get("detections", {}) or {}
    return 1 if int(det.get(key, 0)) == 1 else 0

def split_for_stage12_or_34(record: dict) -> tuple[str, dict]:
   
    flower = to_flag(record, "FLOWER")
    green  = to_flag(record, "GREEN FRUIT")
    red    = to_flag(record, "RED FRUIT")

    has_any = (flower + green + red) > 0

    bucket = "stage34" if has_any else "stage12"

    payload = {
        "filename": record.get("filename"),
        "date": record.get("date"),
        "time": record.get("time"),
        "flags": {
            "FLOWER": flower,
            "GREEN_FRUIT": green,
            "RED_FRUIT": red,
        },
        "raw": record, #raw 데이터 보존
    }

    return bucket, payload
