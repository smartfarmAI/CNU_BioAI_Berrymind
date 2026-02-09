# 🤖 BerryMind 온실 전략 제어 시스템 (Control Logic)

**도메인 지식 기반의 전략 선택 모델을 통해 온실 구동기를 자동 제어합니다.**

---

## 🚀 빠른 시작

```bash
source .venv/bin/activate
python run_control.py --farm-id 2
tail -f control_log.csv
```

**`control_log.csv`에 제어 판단 근거와 명령이 기록됩니다.**

---

## 📁 파일 구조

```
.
├── time_band.py        # 일출/일몰 기준 8개 구간 동적 분할
├── priority_manager.py # 에너지 > 생육안전 > 생산성 우선순위 중재
├── stage_policy.py     # 생육 단계별(S1-S4) 목표 Setpoint 정의
├── safety_guard.py     # 강우/강풍/과습 등 절대 제약조건 처리
├── data_cleaner.py     # 10분 단위 집계 및 결측치 보정 로직
└── run_control.py      # 메인 제어 루프 실행
```

---

## 🎯 제어 흐름

```
센서 데이터 → 데이터 정제 → 타임밴드 결정(T1~T8) → 생육 단계별 목표 → 우선순위 중재 → 구동기 명령
```

---

## 📊 결과 형식 (control_log.csv)

| timestamp | band | stage | fcu | ceiling | fog | reason |
|-----------|------|-------|-----|---------|-----|--------|
| 20260209... | T3 | S3 | ON | 30% | OFF | Temp_Low |

---

## ⚙️ 설정 방법

**1. 생육 단계별 Setpoint (`stage_policy.py`)**
- S1-S4 단계별 EC, pH, 온도 기준 수정
- 단계와 타임밴드 분리 적용

**2. 환경 가드레일**
- `time_band.py`: 온실 위치 설정으로 동적 구간 생성
- `safety_guard.py`: 습도 85% 이상 FOG 가동 금지 등 제약조건 관리

---

## 💡 주요 제어 전략

- **에너지 최적화**: 완충 구간 운영으로 에너지 누수 방지
- **설비 보호**: Pause Time(30분 휴지)로 과동작 차단
- **선제적 대응**: 미래 환경 예측 기반 선제 조절

---

## 📈 주요 명령어

```bash
python run_control.py --mode shadow --date 20260115
python get_actuator_stats.py
```
