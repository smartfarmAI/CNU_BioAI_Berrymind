# 🌱 BerryMind

> **이상기후 적응형 딸기 AI 스마트농업 시스템** > Sensor · SAM3 Vision · Logic-based Strategic Control

<img width="1376" height="572" alt="image" src="[https://github.com/user-attachments/assets/89135c8a-92e0-4d08-96b7-df0757b36028](https://github.com/user-attachments/assets/89135c8a-92e0-4d08-96b7-df0757b36028)" />

## 🔍 Overview

**BerryMind**는 이상기후로 인한 국내 농가의 작물 생산 위기를 해결하기 위해 데이터 기반의 선제적 환경 조절과 객관적인 생육 진단을 수행하는 통합 플랫폼입니다.

본 시스템은 단순히 환경 수치를 유지하는 것을 넘어, 작물의 생리적 특성과 에너지 효율을 고려한 **전략적 자율 제어**를 지향합니다.

* 
**SAM3 기반 식물 생육 진단 (Vision):** SAM3를 활용해 딸기의 꽃, 미숙과, 숙과를 정밀하게 분할하고, 이를 시간 순서로 누적하여 연속적인 생육 흐름을 재구성합니다.


* 
**환경 예측 및 정밀 인지 (Sensing):** 온습도, , 조도 등 다변량 데이터를 10분 단위 윈도우로 분할하여 결측치 보정 및 미래 환경을 예측합니다.


* 
**전략적 자율 제어 (Logic Engine):** 일출/일몰 리듬에 따른 8개 구간(Time-Band) 분할과 에너지-안전-생산성 순위의 중재 로직을 통해 효율적인 제어를 수행합니다.



https://github.com/user-attachments/assets/78771a01-b6aa-433d-bf90-77a40f3cbadb

---

## 📂 Project Structure

### [🍓 SAM3 생육 단계 분석 시스템](https://www.google.com/search?q=./vision_model)

* 
**SAM3 Pipeline:** SAM3 엔진을 통한 객체 탐지 및 Zero-shot Segmentation을 수행합니다.


* 
**Stage Decision:** 인식된 생육 요소를 바탕으로 S1(정식)부터 S4(수확)까지의 생육 단계를 자동 판정합니다 .



### [🤖 온실 전략 제어 시스템](https://www.google.com/search?q=./control_logic)

* 
**Time-Band Manager:** 위도/경도 기반 일출·일몰 시간을 예측하여 8개의 가변적 제어 구간을 생성합니다.


* 
**Priority Rule Engine:** 설비 보호를 위한 Pause Time 전략과 야간 과습 방지 등 절대 가드레일을 포함한 중재 로직을 실행합니다.

