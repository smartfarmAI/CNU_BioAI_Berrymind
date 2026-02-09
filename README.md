🌱 BerryMind

이상기후 적응형 딸기 AI 스마트농업 시스템  
**Sensor · SAM3 Vision · Logic-based Strategic Control**

<img width="1376" height="572" alt="시스템 아키텍처" src="https://github.com/user-attachments/assets/89135c8a-92e0-4d08-96b7-df0757b36028" />

## 🔍 개요

**BerryMind**는 이상기후로 인한 생산 위기를 해결하는 통합 AI 플랫폼입니다.

**핵심 목표**: 단순 환경 유지 → **생리적 특성 + 비용 효율성 고려한 전략적 자율 제어**

### 📊 3대 기술 통합 파이프라인
- **SAM3 Vision**: YOLOv5 대비 **100% 생육 단계 분류 정확도**
- **환경 예측 Sensing**: 10분 단위 다변량 데이터 분석 + 결측 보정
- **Logic Engine**: Time-Band(T1~T8) + 에너지-안전 우선순위 중재

**성과**: 노동력 **74.2% 절감**, 평균 당도 **13.43 Brix**

<img width="100%" alt="성과 비교" src="https://github.com/user-attachments/assets/78771a01-b6aa-433d-bf90-77a40f3cbadb" />

---

## 📂 프로젝트 구조

### 🍓 [SAM3 생육 단계 분석 시스템](./vision_model)

```
이미지 → SAM3 Segmentation → S1(정식) ~ S4(수확) 자동 판정
```
- 딸기 꽃/미숙과/숙과 **정밀 객체 탐지**
- 시간 순서 재구성으로 **전 생육주기 추적**

### 🤖 [온실 전략 제어 시스템](./control_logic)

```
센서 → Time-Band(T1~T8) → 우선순위 중재 → 구동기 제어
```
- **위치 기반 동적 8구간** 제어 (일출/일몰 기준)
- **에너지 최소화 + 설비 보호(Pause Time)** 로직

---
