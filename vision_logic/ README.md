# 🌱 SAM3 토마토 생육 단계 분석 시스템

**토마토 생육 단계(S1-S4)를 SAM3로 자동 판정합니다.**

---

## 🚀 빠른 시작

```bash
python3 -m venv .venv
source .venv/bin/activate
chmod +x setup.sh
./setup.sh
mkdir -p images
cp *.png images/
python run_pipeline.py
```

**`out.csv`에 결과가 저장됩니다.**

---

## 📁 파일 구조

```
.
├── setup.sh           # 환경 설정
├── hf_token.txt       # HF 토큰 (수정 필요)
├── run_pipeline.py    # 전체 실행
├── image_sam3_box.py  # SAM3 탐지
├── images/            # 입력 이미지
└── out.csv            # 결과 파일
```

---

## 🎯 파이프라인 흐름

```
images/*.png → SAM3 → jsondir/*.json → stage 판정 → out.csv
```

---

## 📊 결과 형식 (out.csv)

| filename | date | flower | greenfruit | redfruit | stage | routeto |
|----------|------|--------|------------|----------|-------|---------|
| 20260209...png | 2026-02-09 | 1 | 0 | 0 | S3 | stage34 |

---

## ⚙️ 설정 방법

**1. HF 토큰 설정**
```
[huggingface.co/settings/tokens] → New token(Read) → hf_token.txt에 저장
```

**2. 이미지 준비**
```
YYYYMMDDHHMMSS-position.png 형식으로 images/ 폴더에 저장
```

---

## 💡 주요 명령어

```bash
python run_pipeline.py --detector-confidence 0.5
python get_today_stage.py
deactivate
```
