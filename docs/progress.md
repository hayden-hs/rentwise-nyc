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

### 남은 작업

- [ ] fetch_comps 더미 데이터를 실제 API 호출로 교체 (API 미정)

**파일 위치**: backend/agents/zillow_agent.py
