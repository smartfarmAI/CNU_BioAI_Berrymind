# 🤖 BerryMind 온실 전략 제어 시스템 (Control Logic)

**도메인 지식 기반의 전략 선택 모델을 통해 온실 구동기를 자동 제어합니다.**

---

## 🚀 빠른 시작

```bash
# 1. 가상환경 활성화 (이미 되어있다면 생략)
source .venv/bin/activate

# 2. 제어 엔진 실행
python run_control.py --farm-id 2

# 3. 실시간 제어 로그 확인
tail -f control_log.csv

```

**`control_log.csv`에 모든 제어 판단 근거와 구동기 명령이 기록됩니다.**

---

## 📁 파일 구조

```
.
[cite_start]├── time_band.py         # 일출/일몰 기준 8개 구간 동적 분할 [cite: 303, 308]
[cite_start]├── priority_manager.py  # 에너지 > 생육안전 > 생산성 우선순위 중재 [cite: 302, 305]
[cite_start]├── stage_policy.py      # 생육 단계별(S1-S4) 목표 Setpoint 정의 [cite: 147-150]
[cite_start]├── safety_guard.py      # 강우/강풍/과습 등 절대 제약조건 처리 [cite: 304, 391]
[cite_start]├── data_cleaner.py      # 10분 단위 집계 및 결측치 보정 로직 [cite: 400, 411]
└── run_control.py       # 메인 제어 루프 실행

```

---

## 🎯 제어 흐름

```
[cite_start]센서 데이터 수집 → 데이터 정제 및 결측 보정 [cite: 411] [cite_start]→ 타임밴드 결정(T1~T8) [cite: 303] [cite_start]→ 생육 단계별 목표 매칭 [cite: 144] [cite_start]→ 우선순위 중재 [cite: 305] → 구동기 제어 명령

```

---

## 📊 결과 형식 (control_log.csv)

| timestamp | band | stage | fcu | ceiling | fog | reason |
| --- | --- | --- | --- | --- | --- | --- |
| 20260209... | T3 | S3 | ON | 30% | OFF | Temp_Low |

---

## ⚙️ 설정 방법

**1. 생육 단계별 Setpoint 설정 (`stage_policy.py`)**

* 정식/출뢰/개화/수확기별로 정의된 최적 EC, pH, 온도 기준을 수정합니다 .


* 각 단계별 이원화 설계(단계와 타임밴드 분리)를 적용합니다.



**2. 환경 가드레일 및 위치 설정**

* 
`time_band.py`에서 온실 위치 정보를 설정하여 생리주기 기반 동적 구간을 생성합니다.


* 
`safety_guard.py`에서 습도 85% 이상 시 FOG 가동 금지 등 절대 제약조건을 관리합니다.



---

## 💡 주요 제어 전략 (Control Strategy)

* 
**에너지 최적화:** 타이트한 고정 온도 제어를 지양하고 완충 구간을 운영하여 에너지 누수를 방지합니다.


* 
**설비 보호:** Pause Time 전략(30분 휴지)을 통해 구동기 과동작 및 토글 현상을 구조적으로 차단합니다.


* 
**선제적 대응:** 과거 데이터 기반 사후 대응이 아닌, 미래 환경 예측을 통한 선제적 조절을 수행합니다.



---

## 📈 주요 명령어

```bash
# 특정 날짜의 제어 시뮬레이션 (Shadow Deployment)
[cite_start]python run_control.py --mode shadow --date 20260115 [cite: 581]

# 구동기 동작 횟수 및 에너지 절감 통계 확인
[cite_start]python get_actuator_stats.py [cite: 660, 673]

```
