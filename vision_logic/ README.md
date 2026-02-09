# SAM3 생육 단계 분석 시스템

**토마토 생육 단계(S1-S4)를 SAM3로 자동 판정하는 파이프라인입니다.**

***

## 🚀 빠른 시작

HuggingFace 토큰 발급 및 설정 (필수)
SAM 3 모델 가중치 접근을 위해 토큰 설정이 필요합니다.

HuggingFace Settings에서 Read 권한의 토큰을 생성합니다.

프로젝트 루트 폴더의 hf_token.txt 파일을 열고 발급받은 토큰을 붙여넣습니다.

Bash
echo "your_token_here" > hf_token.txt

```bash
# 1. 가상환경 생성 & 활성화
python3 -m venv .venv
source .venv/bin/activate

# 2. 환경 설정
chmod +x setup.sh
./setup.sh

# 3. 이미지 넣고 실행
mkdir images
cp *.png images/
python run_pipeline.py

**완료 시 `out.csv`에 모든 결과 저장.**

***

## 📁 파일 목록

| 파일 | 역할 |
|------|------|
| `setup.sh` | 환경 설정 |
| `requirements.txt` | 패키지 목록 |
| `hf_token.txt` | HF 토큰 (수정 필요) |
| `run_pipeline.py` | 전체 파이프라인 실행 |
| `image_sam3_box.py` | SAM3 탐지 + 바운딩 박스 |
| `splitter_min.py` | stage12/34 분류 |
| `stage12_decider.py` | S1/S2 판정 (시간 기반) |
| `stage34_decider.py` | S3/S4 판정 (꽃/과일 기반) |
| `FILE_GUIDE.md` | 상세 가이드 |

***

## 🎯 파이프라인 흐름

```
images/ (.png)
    ↓ image_sam3_box.py
json_dir/ (.json)
    ↓ splitter_min.py
stage12/34 분기
    ↓ stage12_decider.py / stage34_decider.py
out.csv (최종 결과)
```

***

## 📊 결과 (out.csv)

| 컬럼 | 설명 |
|------|------|
| `filename` | 이미지 파일명 |
| `date` | 촬영 날짜 |
| `flower` | 꽃 탐지 (0/1) |
| `greenfruit` | 녹색과일 (0/1) |
| `redfruit` | 붉은과일 (0/1) |
| `stage` | **S1(정식) / S2(생장) / S3(개화) / S4(수확)** |
| `routeto` | 판정 경로 (stage12/34) |

***

## 💡 주요 명령어

```bash
# 전체 파이프라인
python run_pipeline.py

# SAM3 탐지만 (바운딩 박스 생성)
python image_sam3_box.py --image_folder ./images

# 가상환경 끄기
deactivate
```

***

## ⚙️ 설정

1. **HF 토큰** 수정: `hf_token.txt`에 본인 토큰 입력
2. **이미지 형식**: `YYYYMMDDHHMMSS-position.png`
3. **신뢰도**: `run_pipeline.py`에서 `--detector-confidence 0.5` 조정 가능

***

## 📈 오늘 단계 확인

```bash
python get_today_stage.py
# 출력 예시:
# 2026-01-09: S3
```

***

**설치 후 바로 `python run_pipeline.py` 실행하세요!** 🎉
