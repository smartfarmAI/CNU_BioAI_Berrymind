# SFAI 2025 - 스마트팜 AI 경진대회

## 프로젝트 개요

이 프로젝트는 2025년 스마트농업 AI 경진대회를 위한 통신인터페이스 예시입니다. 
KSB7958 폴더는 표준 통신 프로토콜을 사용하여 센서 데이터를 읽고, 구동기를 제어하는 샘플입니다.
extra 폴더는 비표준 인터페이스에 대한 샘플입니다.

## 디렉토리 구조

```
/
├── extra/
│   ├── client.py: 서버와 통신하는 클라이언트 
│   ├── conf.json: 설정 파일
│   ├── sample.py: 간단한 샘플 코드
│   └── forecasts/
│       └── forecast.json: 기상 예보 데이터 예시 (기상청 OPENAPI 참고)
├── KSB7958/
│   ├── conf.json: 설정 파일
│   ├── ksconstants.py: 프로젝트에서 사용하는 상수
│   ├── control_priv.py: 제어권 변경 샘플 (대회에서 사용할 필요는 없음)
│   ├── nutsupply.py: 양액공급기 제어
│   ├── read_sensor.py: 센서 데이터 리딩
│   ├── retractable.py: 개폐기 제어
│   └── switch.py: 스위치 제어
├── requirements.txt: 프로젝트 의존성 목록
└── README.md: 프로젝트 설명
```

## 주요 기능

*   **센서 데이터 수집:** `KSB7958/read_sensor.py`를 통해 다양한 센서(온도, 습도 등)로부터 데이터를 수집합니다.
*   **양액 공급 제어:** `KSB7958/nutsupply.py`를 통해 작물에 필요한 양액을 자동으로 공급합니다.
*   **개폐기 및 스위치 제어:** `KSB7958/retractable.py` 및 `switch.py`를 통해 스마트팜의 물리적 환경을 제어합니다.
*   **외부 데이터 연동:** `extra/client.py`를 통해 외부 API(예: 기상 정보)와 연동하여 제어 로직에 활용할 수 있습니다.

## 설치 및 실행

1.  **저장소 복제:**
    ```bash
    git clone (repository_url)
    cd sfai25
    ```

2.  **가상환경 생성 및 활성화:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```

3.  **의존성 설치:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **실행:**
    ```bash
    cd KSB7958; python read_sensor.py
    cd extra; python sample.py
    ```

## 설정

extra 폴더의 설정은 `extra/conf.json` 파일에서 변경할 수 있습니다.
KSB7958 폴더의 설정은 `KSB7958/conf.json` 파일에서 변경할 수 있습니다.

## 라이선스

이 프로젝트는 MIT 라이선스를 따릅니다. 자세한 내용은 `LICENSE` 파일을 참고하세요.
