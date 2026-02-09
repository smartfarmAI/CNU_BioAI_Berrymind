# 🌱 BerryMind

**이상기후 적응형 딸기 AI 스마트농업 시스템**  
**Sensor · SAM3 Vision · Logic-based Strategic Control**

<img width="1376" height="572" alt="시스템 아키텍처" src="https://github.com/user-attachments/assets/89135c8a-92e0-4d08-96b7-df0757b36028" />

## 🔍 개요

**BerryMind**는 이상기후로 인한 국내 농가의 작물 생산 위기를 극복하고 지속 가능한 정밀 농업을 실현하는 통합 관리 플랫폼입니다.

단순 센서 수치 유지 → **작물 생리 + 에너지 효율**을 고려한 **전략적 자율 제어**

<img width="100%" alt="성과" src="https://github.com/user-attachments/assets/78771a01-b6aa-433d-bf90-77a40f3cbadb" />

---

## 🎯 프로젝트 목표

- **정밀 생육 인지**: SAM3로 딸기 꽃/미숙과/숙과 픽셀 단위 분할 → S1~S4 자동 판정
- **이상기후 대응**: 한파/폭염/다우점 등 선제적 제어 로직
- **에너지 최적화**: Time-Band + Priority Rule로 운영비 절감
- **현장 신뢰성**: 농민 도메인 지식 + AI 판단 결합

---

## 🛠️ 핵심 기술

| 기술 | 기능 |
|------|------|
| **SAM3 Vision** | 꽃/미숙과/숙과 정밀 Segmentation → 생육 데이터 수치화 |
| **환경 Sensing** | 10분 단위 다변량 분석 + 결측치 보정 |
| **Logic Engine** | Time-Band(T1~T8) + 에너지/안전 우선순위 중재 |

---

## 📂 프로젝트 구조

### 🍓 **SAM3 생육 단계 분석** `./vision_model`
- **SAM3 Pipeline**: Zero-shot Segmentation으로 생리 지표 추출
- **Stage Decision**: S1(정식) ~ S4(수확) 자동 판정 + 누적 안정화

### 🤖 **온실 전략 제어** `./control_logic`
- **Time-Band Manager**: 위/경도 기반 8개 동적 구간 생성
- **Priority Engine**: Pause Time + 야간 과습 가드레일 포함

**모듈화 설계로 타 작물/온실 확장 가능**
