# RentWise 학습 개념 정리

> 새로 배운 개념이 생길 때마다 이 파일에 이어서 추가한다.
> 목표: "그때는 이해했는데 나중엔 기억 안 남" 문제를 없애는 것.
> 각 항목은 본인 언어로 다시 요약하는 걸 원칙으로 한다 (Feynman 기법).

---

## LangChain vs LangGraph

- **LangChain** = LLM 호출을 조합하는 컴포넌트 라이브러리 (PromptTemplate, LCEL, 체인, 메모리, 리트리버 등). 실행 흐름이 기본적으로 선형적.
- **LangGraph** = LangChain 위에 만들어진 오케스트레이션 레이어. 그래프(노드+엣지) 구조로 실행 흐름을 설계하고, State를 명시적으로 관리. 조건부 분기, 반복, 체크포인트, Human-in-the-loop이 자연스럽게 가능.
- 비유: LangChain = 재료, LangGraph = 재료를 순서대로 조리하는 레시피 판.

**LangGraph가 해결하는 3가지 문제** (LangGraph Essentials 코스 인트로 기준):

| 문제 | 원인 | 해결책 |
|---|---|---|
| Latency (레이턴시) | LLM 응답이 ms가 아니라 초 단위로 걸림 | Parallelization(실제 대기시간 ↓), Streaming(체감 대기시간 ↓) |
| Reliability (신뢰성) | 오래 도는 에이전트가 중간 실패하면 처음부터 재실행해야 해서 비용/시간 큼 | Checkpointing — 매 단계마다 state 저장, 실패 지점부터 재개 가능 |
| Non-determinism (비결정성) | 같은 입력에도 LLM 응답이 매번 다를 수 있음 | Human-in-the-Loop(승인/개입), LangSmith(tracing/evaluation) |

**RentWise 적용**: Phase 1은 순차 오케스트레이션이라 레이턴시 손해를 감수하는 대신 스코프를 단순하게 유지 (Phase 2에서 병렬화 예정). Checkpointing 덕분에 Zillow 성공, HPD 실패 시 처음부터가 아니라 HPD부터 재시도 가능 — 이게 "왜 단순 함수 호출이 아니라 LangGraph인가"에 대한 핵심 답변 근거.

---

## Latency (레이턴시)

요청을 보내고 응답이 돌아올 때까지 걸리는 지연 시간.

- 순차 오케스트레이션 = 각 단계 레이턴시가 그대로 더해짐 (Zillow + HPD + 311 순서대로 대기)
- 병렬 오케스트레이션 = 가장 오래 걸리는 작업 하나의 시간만큼만 대기
- Streaming = 전체 결과를 기다리지 않고 부분 결과를 바로바로 보여줘서 체감 대기시간을 줄이는 방식

---

## State, Node, Edge (LangGraph 핵심 3요소)

Caspar(LangGraph Essentials 강사)의 비유: LangGraph는 하나의 프로그래밍 언어와 같다.

- **State** = 그래프를 흐르는 데이터. 모든 노드가 공유.
- **Node** = 데이터를 처리하는 함수 (input: state, output: state에 대한 update)
- **Edge** = 흐름 제어. static/conditional, parallel/series 가능 — 프로그램의 논리 분기와 비슷한 역할

**StateGraph 동작 원리**:
- State는 그래프에 공급되고, 그래프에 의해 업데이트되고, 사용자에게 반환됨
- **그래프 자체는 stateless** — 로직만 갖고 있고 데이터(state)는 실행할 때마다 외부에서 주입됨
- 실행 흐름: `invoke()` → state 초기화 → 런타임이 실행할 노드 선택 → 그 노드에 현재 state 공급 → 노드 실행 → 결과로 state 업데이트

---

## TypedDict

파이썬 `typing` 모듈의 도구. 이름 그대로 "Typed" + "Dict" — 타입이 지정된 딕셔너리.

```python
class State(TypedDict):
    nlist: list[str]
```

- `class State(TypedDict):` → `TypedDict`는 함수 인자가 아니라 **상속**하는 부모 클래스. "State는 TypedDict의 기능을 물려받아 만든다"는 뜻
- `nlist: list[str]` → 클래스 속성의 **타입 선언(annotation)**. "이 클래스는 nlist라는 칸을 가지고, 그 칸엔 문자열 리스트만 들어와야 한다"는 규칙. `=`가 아니라 `:`이므로 값을 대입하는 게 아니라 타입만 정의하는 것
- **핵심**: TypedDict로 만든 클래스는 런타임엔 그냥 평범한 `dict`. 코드에서 `state['nlist']`처럼 대괄호(딕셔너리 문법)로 접근하는 게 그 증거. 점 표기법(`state.nlist`)이 아님
- State는 TypedDict 외에 Python dataclass, Pydantic BaseModel로도 정의 가능 (강사는 단순함 때문에 TypedDict 선택)

**클래스 상속 문법 감 잡기**:
```python
class 자식클래스(부모클래스):
```
괄호 안은 인자가 아니라 부모 클래스. `class Dog(Animal):`과 동일한 문법.

**클래스에 괄호 붙여서 호출하는 경우** (다른 용법, 헷갈리지 말 것):
```python
State(nlist=[note])
```
이건 상속이 아니라 **인스턴스 생성** — State 틀에 실제 값을 채워서 진짜 딕셔너리 하나를 만드는 것. `{"nlist": [note]}`와 동일.

---

## LangGraph 최소 예제 (Lab 1: States & Nodes)

```python
from IPython.display import Image, display
from typing import TypedDict
from langgraph.graph import END, START, StateGraph

# 1. State 정의
class State(TypedDict):
    nlist: list[str]

# 2. Node 정의 — state 받아서 update 리턴
def node_a(state: State) -> State:
    print(f"node a is receiving {state['nlist']}")
    note = "Hello World from Node a"
    return State(nlist=[note])

# 3. 그래프 조립
builder = StateGraph(State)
builder.add_node("a", node_a)
builder.add_edge(START, "a")
builder.add_edge("a", END)
graph = builder.compile()

# 4. 시각화
display(Image(graph.get_graph().draw_mermaid_png()))

# 5. 실행
initial_state = State(nlist=["Hello Node a, how are you?"])
graph.invoke(initial_state)
```

**핵심 확인 포인트**: 입력값(`"Hello Node a, how are you?"`)이 `node_a`를 거치며 완전히 새 값(`"Hello World from Node a"`)으로 **덮어써짐(overwritten)**. 노드가 state를 업데이트한다는 것의 실제 증거.

**RentWise 3-agent 구조로 확장하면**:

| Lab 1 | RentWise Phase 1 |
|---|---|
| `nlist: list[str]` | `address`, `zillow_result`, `hpd_result`, `311_result`, `score` |
| `node_a` 하나 | `zillow_agent`, `hpd_agent`, `agent_311` 세 개 |
| `START → a → END` | `START → zillow → hpd → 311 → END` |

```python
builder.add_node("zillow", zillow_agent)
builder.add_node("hpd", hpd_agent)
builder.add_node("311", agent_311)
builder.add_edge(START, "zillow")
builder.add_edge("zillow", "hpd")
builder.add_edge("hpd", "311")
builder.add_edge("311", END)
```

---

## 개발 환경 / 셋업 관련 메모

- **uv** = pip + venv + pyenv를 합친 Python 올인원 도구. `uv sync` 한 줄로 가상환경 생성 + Python 버전 맞춤 + 패키지 설치까지 처리.
- **커널(Jupyter)** = 노트북 코드를 실제로 실행하는 Python 환경. 여러 프로젝트를 진행하면 같은 이름의 커널이 다른 venv를 가리키는 경우가 있어 혼동 주의 — `import sys; print(sys.executable)`로 실제 연결된 Python 경로 확인 습관화.
- API 키는 **절대 채팅창에 붙여넣지 않기**. 실수로 노출됐다면 즉시 해당 플랫폼에서 revoke 후 재발급.

---

## Grilling 대비 메모 (레쥬메 프로젝트 방어 포인트)

- **왜 LangGraph인가 (vs 단순 함수 호출)**: Checkpointing으로 중간 실패 시 재시도 가능, 순수 함수 체인은 실패 시 상태 복구 불가
- **왜 순차 오케스트레이션인가 (Phase 1)**: 스코프를 단순하게 유지하고 병렬화는 Phase 2로 명확히 분리한 의도적 결정
- **MTA/ACRIS 스코프 제외 이유**: Google Maps(MTA), JustFix "Who Owns What"(ACRIS)과 데이터 중복 — 차별화는 데이터 수집이 아니라 종합/판단(synthesis) 레이어에 있다는 논리
