# RentWise NYC — Progress Log

## Zillow Agent

### 설계 결정

| 결정 사항        | 확정 내용                                                           | 이유                                                                                          |
| ---------------- | ------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| 입력 시나리오    | 주소 + 임대료 + 방개수 (사용자 직접 입력)                           | 주소만으론 다세대 건물 매칭 문제, 비활성 리스팅 케이스 처리 불가                              |
| API 소싱         | 나중에 결정 (Zillapi/RentCast/HUD FMR 등)                           | Zillow 직접 스크래핑은 ToS 위반. State 설계엔 영향 없어서 실제 코딩 직전에 결정해도 무방      |
| 적정성 판단 방식 | 통계는 코드가 계산 (평균, %차이, threshold 기반 라벨), GPT는 설명만 | 산술 정확도, 재현성, LangSmith eval 설계 용이성, 면접 방어력                                  |
| 협상 코멘트 범위 | Zillow agent는 "가격 기준" 간단 코멘트만 담당                       | 계약조건 등 폭넓은 협상 조언은 HPD/311까지 합쳐야 근거 충분 — 최종 synthesis 단계 몫으로 미룸 |

### 노드 다이어그램

[fetch_comps] → [compute_stats] → [explain_verdict]

기술 난이도는 Lab 1 수준 (순차 실행). HPD/311 합칠 때(Lab 3 이상 개념) 고려할 문제라 지금은 무시.
각 agent 결과를 nested TypedDict로 캡슐화 → 나중에 reducer 없이도 병합 가능.

### State 구조

```python
class CompListing(TypedDict):
    address: str
    rent: float
    bedrooms: int

class ZillowAgentState(TypedDict):
    address: str
    user_rent: float
    bedrooms: int
    comps: list[CompListing]
    avg_comp_rent: float
    diff_pct: float
    verdict_label: Literal["overpriced", "underpriced", "fair"]
    price_explanation: str
    negotiation_comment: str

class VerdictExplanation(TypedDict):
    price_explanation: str
    negotiation_comment: str
```

### 완료

- [x] 입력/판단 방식/노드 다이어그램 설계 확정
- [x] CompListing, ZillowAgentState, VerdictExplanation TypedDict 작성
- [x] fetch_comps 함수 작성 (더미 comp 데이터로 임시 구현)
- [x] compute_stats 함수 작성
- [x] explain_verdict 함수 작성 (with_structured_output 사용)
- [x] StateGraph 빌드 (builder.add_node x3, add_edge x4, compile)
- [x] .env에 OPENAI_API_KEY 있는지 확인
- [x] graph.invoke()로 전체 파이프라인 실행 테스트
- [x] fetch_comps를 RentCast `/avm/rent/long-term` 실제 API 호출로 교체
- [x] try/except(requests.exceptions.RequestException)로 API 실패 시 fallback_comps 전환 처리
- [x] response.raise_for_status()로 4xx/5xx 응답 명시적 예외 처리
- [x] 실행 로그로 fallback 전환 정상 작동 확인 (401 Unauthorized → except 블록 발동 확인)

### 남은 작업

- [ ] RentCast 구독 여부 결정 (무료 Developer 티어도 카드 등록 필요 — 카드 등록 부담으로 보류 중, Phase 1 마감 전 판단)
- [ ] fallback_comps 값 다양화 (현재 3개 comp가 전부 동일 값이라 데모 설득력 낮음 — 주소/임대료 다르게 조정)
- [ ] HPD agent 설계 시작

**파일 위치**: backend/agents/zillow_agent.py

## HPD Agent

### 설계 결정

| 결정 사항              | 확정 내용                                                                                         | 이유                                                                                  |
| ---------------------- | ------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| 데이터셋 스코프        | 5개 (Violation Files, AEP, Charges/OMO, Litigation, Orders)                                       | "검증된 violation + 강제조치"만 포함, raw complaint 성격(311 영역)은 제외             |
| 노드 분할              | 5개 데이터셋 → 2개 노드로 그룹핑 (Violation 단독 + 나머지 4개 통합)                               | 부분 실패 처리 복잡도는 노드 개수와 무관, Zillow 구조와의 유사성 유지                 |
| 주소→BBL 변환          | 별도 `geocode_address` 노드로 분리 (NYC Geoclient API)                                            | 5개 데이터셋 전부가 공통으로 bbl 필요, 지오코딩과 데이터조회는 다른 책임              |
| EnforcementRecord 구조 | 4개 소스 공통 필드(source/date/description/is_active) + 소스 전용 필드(amount, is_landlord_fault) | 이종 데이터를 하나의 리스트로 통합해 compute_stats에서 균일하게 순회                  |
| 판단 방식              | compute_stats가 점수/등급 계산, GPT는 explain만                                                   | Zillow와 동일한 원칙 유지                                                             |
| 점수 임계값            | 실측 데이터(건물 174,370개) 분포 기반으로 확정                                                    | 감으로 잡은 기준은 실제 분포와 크게 어긋날 위험 (Charges 금액 구간에서 실제로 확인됨) |

### 노드 다이어그램

```
[geocode_address] → [fetch_violations] → [fetch_enforcement] → [compute_stats] → [explain_verdict]
```

Lab 1 수준 직렬 구조 유지. `fetch_enforcement` 내부에서 asyncio.gather로 4개 API 병렬 호출하지만, 그래프 구조 자체는 갈라지지 않음(Lab 2 불필요).

### State 구조

```python
class ViolationRecord(TypedDict):
    violationid: str
    class_: str
    novdescription: str
    inspectiondate: str
    violationstatus: str
    rentimpairing: bool

class EnforcementRecord(TypedDict):
    source: Literal["AEP", "Charges", "Litigation", "Order"]
    date: str
    description: str
    is_active: bool
    is_landlord_fault: bool | None   # Charges 전용
    amount: float | None              # Charges 전용

class HPDAgentState(ZillowAgentState):
    bbl: str
    geocoding_success: bool
    hpd_violations: list[ViolationRecord]
    violations_fetch_success: bool
    hpd_enforcement_records: list[EnforcementRecord]
    enforcement_fetch_success: bool
    violation_score: float
    enforcement_score: float
    hpd_severity_label: Literal["good", "caution", "danger"]

class HPDVerdictExplanation(TypedDict):
    severity_explanation: str
    negotiation_comment: str
```

### compute_stats 계산식

```
violation_score = Σ [ (class_weight × status_weight) + rentimpairing_bonus ]
enforcement_score = Σ [ (1 × active_weight) + amount_bonus ]

severity_label:
    total_score < 5   → "good"
    total_score < 45  → "caution"
    total_score >= 45 → "danger"
```

가중치/구간/임계값 상세 근거는 `concepts.md` 참고.

### 완료

- [x] 5개 데이터셋 필드 확정 (Violation Files, AEP, Charges, Litigation, Orders)
- [x] `ViolationRecord`, `EnforcementRecord` TypedDict 작성
- [x] `HPDAgentState` (ZillowAgentState 상속) 작성
- [x] `HPDVerdictExplanation` TypedDict 작성
- [x] `compute_stats` 계산식 확정 (실측 데이터 174,370개 건물 기준 임계값 검증)
- [x] Geoclient API 키 발급 절차 확인

### 남은 작업

- [ ] Geoclient API 키 발급 완료
- [ ] `geocode_address` 노드 코딩
- [ ] `fetch_violations` 노드 코딩
- [ ] `fetch_enforcement` 노드 코딩 (asyncio.gather 4개 소스)
- [ ] `compute_stats` 노드 코딩
- [ ] `explain_verdict` 노드 코딩
- [ ] StateGraph 조립 + `graph.invoke()` 테스트

**파일 위치**: `backend/agents/hpd_agent.py`
