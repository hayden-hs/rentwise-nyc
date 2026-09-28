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
- [x] 파일 맨 아래 실행부를 `if __name__ == "__main__":`으로 감싸기 (다른 파일이 import할 때 자동 실행되는 부작용 방지)

### 남은 작업

- [ ] RentCast 구독 여부 결정 (무료 Developer 티어도 카드 등록 필요 — 카드 등록 부담으로 보류 중, Phase 1 마감 전 판단)
- [ ] fallback_comps 값 다양화 (현재 3개 comp가 전부 동일 값이라 데모 설득력 낮음 — 주소/임대료 다르게 조정)

**파일 위치**: backend/agents/zillow_agent.py

## HPD Agent

### 설계 결정

| 결정 사항                        | 확정 내용                                                                                               | 이유                                                                                              |
| -------------------------------- | ------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| 데이터셋 스코프                  | 5개 (Violation Files, AEP, Charges/OMO, Litigation, Orders)                                             | "검증된 violation + 강제조치"만 포함, raw complaint 성격(311 영역)은 제외                         |
| 노드 분할                        | 5개 데이터셋 → 2개 노드로 그룹핑 (Violation 단독 + 나머지 4개 통합)                                     | 부분 실패 처리 복잡도는 노드 개수와 무관, Zillow 구조와의 유사성 유지                             |
| 주소→BBL 변환                    | 별도 `geocode_address` 노드로 분리 (NYC Geoclient API `/search` 엔드포인트)                             | 5개 데이터셋 전부가 공통으로 bbl 필요, 지오코딩과 데이터조회는 다른 책임                          |
| EnforcementRecord 구조           | 4개 소스 공통 필드(source/date/description/is_active) + 소스 전용 필드(amount, is_landlord_fault)       | 이종 데이터를 하나의 리스트로 통합해 compute_stats에서 균일하게 순회                              |
| 판단 방식                        | compute_stats가 점수/등급 계산, GPT는 explain만                                                         | Zillow와 동일한 원칙 유지                                                                         |
| 점수 임계값                      | 실측 데이터(건물 174,370개) 분포 기반으로 확정                                                          | 감으로 잡은 기준은 실제 분포와 크게 어긋날 위험 (Charges 금액 구간에서 실제로 확인됨)             |
| fetch_enforcement 동시성 방식    | `httpx` + `asyncio.gather` 채택 (requests 대신)                                                         | requests는 동기 전용이라 4개 API 병렬 호출 불가. httpx는 async/await 지원                         |
| fetch_enforcement 부분 실패 처리 | `asyncio.gather(..., return_exceptions=True)` + `isinstance(x, Exception)`으로 개별 소스 성공/실패 판단 | 4개 중 일부만 실패해도 나머지 소스 결과는 살리기 위함 (기본 gather는 하나 실패 시 전체 결과 버림) |
| fetch_enforcement 내부 구조      | AEP/Charges/Litigation/Orders를 공통 반복문이 아니라 4개의 독립된 블록으로 작성                         | 4개 소스의 원본 필드명이 전부 달라, 억지로 반복문 하나로 묶으면 오히려 분기 처리가 더 복잡해짐    |

### 노드 다이어그램

```
[geocode_address] → [fetch_violations] → [fetch_enforcement] → [compute_stats] → [explain_verdict]
```

Lab 1 수준 직렬 구조 유지. `fetch_enforcement` 내부에서 asyncio.gather로 4개 API 병렬 호출하지만, 그래프 구조 자체는 갈라지지 않음(Lab 2 불필요) — 이건 노드 하나 안에서의 Python 레벨 동시성이지 LangGraph 그래프 레벨 병렬 분기가 아님.

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
    is_landlord_fault: Optional[bool]   # Charges 전용 (Python 3.9 환경이라 `bool | None` 대신 Optional 사용)
    amount: Optional[float]              # Charges 전용

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

### URL 상수

```python
GEOCLIENT_URL = "https://api.nyc.gov/geoclient/v2/search"
VIOLATIONS_URL = "https://data.cityofnewyork.us/resource/wvxf-dwi5.json"
AEP_URL = "https://data.cityofnewyork.us/resource/hcir-3275.json"
CHARGES_URL = "https://data.cityofnewyork.us/resource/mdbu-nrqn.json"
LITIGATION_URL = "https://data.cityofnewyork.us/resource/59kj-x8nc.json"
ORDERS_URL = "https://data.cityofnewyork.us/resource/tb8q-a3ar.json"
```

### fetch_enforcement 소스별 매핑 (2026-09-27 확정)

```python
NOT_LANDLORD_FAULT_REASONS = ["duplicate omo", "utility account picked up by esb", "vacant land",
    "apt. vacant", "bldg. vacant", "user error", "condition not found",
    "condition does not exist", "for field visits only - cancelled"]
```

| 필드                | AEP                              | Charges                 | Litigation                | Order                            |
| ------------------- | -------------------------------- | ----------------------- | ------------------------- | -------------------------------- |
| `source`            | `"AEP"`                          | `"Charges"`             | `"Litigation"`            | `"Order"`                        |
| `date`              | `aep_start_date`                 | `omocreatedate`         | `caseopendate`            | `vacate_effective_date`          |
| `description`       | B/C 위반 수 문장                 | `omodescription`        | `casetype` 문장           | 사유+유형 문장                   |
| `is_active`         | `current_status == "AEP Active"` | 항상 `False`            | `casestatus == "PENDING"` | `"actual_rescind_date" not in c` |
| `is_landlord_fault` | `None`                           | 블랙리스트 기반         | `None`                    | `None`                           |
| `amount`            | `None`                           | `float(omoawardamount)` | `None`                    | `None`                           |

상세 근거와 한계는 `concepts.md` 참고.

### compute_stats 계산식

```
violation_score = Σ [ (class_weight × status_weight) + rentimpairing_bonus ]
enforcement_score = Σ [ (1 × active_weight) + amount_bonus ]

severity_label:
    total_score < 5   → "good"
    total_score < 45  → "caution"
    total_score >= 45 → "danger"
```

가중치/구간/임계값 상세 근거는 `concepts.md` 참고. 아직 코딩 시작 전.

### 완료

- [x] 5개 데이터셋 필드 확정 (Violation Files, AEP, Charges, Litigation, Orders)
- [x] `ViolationRecord`, `EnforcementRecord` TypedDict 작성
- [x] `HPDAgentState` (ZillowAgentState 상속) 작성
- [x] `HPDVerdictExplanation` TypedDict 작성
- [x] `compute_stats` 계산식 확정 (실측 데이터 174,370개 건물 기준 임계값 검증)
- [x] Geoclient API 키 발급 완료 (.env에 GEOCLIENT_APP_KEY 등록)
- [x] Geoclient `/search` 엔드포인트로 확정 (address/houseNumber+street 대신 single-field search 사용)
- [x] `geocode_address` 노드 코딩 완료 + 단독 테스트 통과 ("776 Franklin Ave, Brooklyn, NY, 11238" → bbl "3011787503")
- [x] `fetch_violations` 노드 코딩 완료 + 단독 테스트 통과 (해당 건물 위반 10건 확인: Class A 9건, Class C 1건, rentimpairing 전부 N)
- [x] `fetch_aep`, `fetch_charges`, `fetch_litigations`, `fetch_orders` 헬퍼 코루틴 작성 (httpx.AsyncClient 기반)
- [x] `fetch_enforcement` 노드 뼈대 작성 — `asyncio.gather(..., return_exceptions=True)` + `isinstance` 기반 실패 판별
- [x] AEP/Charges/Litigation/Orders 실제 응답 필드명 확인 (2026-09-27) — NYC Open Data 문서(Columns 표) + 실측 샘플(`$limit`)/집계(`$group`)로 검증. 문서와 실제 값이 다른 지점 다수 발견 (AEP `current_status`, bbl 타입, 키 누락 패턴 등 — `concepts.md` 참고)
- [x] `fetch_enforcement`의 4개 소스별 `EnforcementRecord` 변환 로직 완성 (2026-09-27) — AEP를 직접 작성한 뒤 Charges/Litigation/Order 순으로 완성, 4개 소스 실제 건물(bbl 여러 개)로 테스트 통과
- [x] `fetch_enforcement` 리턴 완성 (2026-09-27) — `hpd_enforcement_records`, `enforcement_fetch_success`(4개 중 하나라도 실패 시 False) 반환. `{'hpd_enforcement_records': [...], 'enforcement_fetch_success': True}` 형태로 검증됨

### 남은 작업

- [ ] `compute_stats` 노드 코딩
- [ ] `explain_verdict` 노드 코딩
- [ ] StateGraph 조립 (`geocode_address → fetch_violations → fetch_enforcement → compute_stats → explain_verdict`) + `graph.invoke()` 테스트

### 일정 메모

- 원래 계획(9/23 필드명 확인 → 9/24 else 블록 → 9/25 compute_stats → 9/26 explain_verdict+조립 → 9/27 테스트/HPD 완성) 대비, 9/23~9/27을 필드명 확인 + else 블록 4개에 다 씀. `compute_stats`부터 3개 항목이 뒤로 밀림
- 이력서 제출일 10/7 기준, 프로젝트 완료 목표를 10/14로 재설정함 (버퍼 3일 포함: 9/29, 10/6, 10/14)
- 다음 세션 시작점: `compute_stats` 코딩

**파일 위치**: `backend/agents/hpd_agent.py`
**실행 명령**: `python -m backend.agents.hpd_agent` (반드시 `rentwise-nyc` 루트 디렉토리에서 실행)
