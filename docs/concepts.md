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

| 문제                       | 원인                                                                     | 해결책                                                          |
| -------------------------- | ------------------------------------------------------------------------ | --------------------------------------------------------------- |
| Latency (레이턴시)         | LLM 응답이 ms가 아니라 초 단위로 걸림                                    | Parallelization(실제 대기시간 ↓), Streaming(체감 대기시간 ↓)    |
| Reliability (신뢰성)       | 오래 도는 에이전트가 중간 실패하면 처음부터 재실행해야 해서 비용/시간 큼 | Checkpointing — 매 단계마다 state 저장, 실패 지점부터 재개 가능 |
| Non-determinism (비결정성) | 같은 입력에도 LLM 응답이 매번 다를 수 있음                               | Human-in-the-Loop(승인/개입), LangSmith(tracing/evaluation)     |

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

| Lab 1              | RentWise Phase 1                                                |
| ------------------ | --------------------------------------------------------------- |
| `nlist: list[str]` | `address`, `zillow_result`, `hpd_result`, `311_result`, `score` |
| `node_a` 하나      | `zillow_agent`, `hpd_agent`, `agent_311` 세 개                  |
| `START → a → END`  | `START → zillow → hpd → 311 → END`                              |

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

---

## Reducer (State 병합 규칙)

- **Reducer** = State 필드에 여러 업데이트가 들어올 때, "덮어쓸지 합칠지"를 정하는 함수. `기존값 = reducer(기존값, 새값)` 방식으로 동작
- 어원은 **MapReduce**의 "reduce" — 여러 값을 하나로 합치는 함수라는 점에서 같은 개념
- **reducer가 없으면 기본 동작 = 덮어쓰기** (Lab 1이 이 경우). 병렬 브랜치가 같은 키를 동시에 쓰면 마지막 쓰기가 이기거나(overwrite), 상황에 따라 `InvalidUpdateError`가 날 수 있음
- reducer는 **필드(키)마다 개별 지정** 가능 — 어떤 필드는 병합, 어떤 필드는 덮어쓰기로 섞어서 쓸 수 있음
- `operator.add` 외에 **직접 만든 커스텀 함수**도 reducer로 쓸 수 있음

**적용 시점 — 세 단계로 분리해서 이해할 것** (헷갈리기 쉬운 부분):

| 시점                  | 코드                                 | 하는 일                                                                         |
| --------------------- | ------------------------------------ | ------------------------------------------------------------------------------- |
| State 클래스 정의     | `Annotated[list[str], operator.add]` | "나중에 이 필드는 이렇게 합쳐라"는 **규칙 등록** (계산 없음)                    |
| 노드 실행             | `return State(nlist=["A"])`          | 단순 **딕셔너리 생성** (`{"nlist": ["A"]}`). `operator.add`는 여기서 호출 안 됨 |
| LangGraph 내부 (자동) | `operator.add(기존값, ["A"])`        | 노드 리턴 직후, **LangGraph가 알아서** 실제 병합 연산 수행                      |

즉 노드는 "내 몫(delta)"만 리턴하고, 실제로 합치는 주체는 노드 코드가 아니라 LangGraph 프레임워크.

---

## Annotated 문법

```python
nlist: Annotated[list[str], operator.add]
```

- `Annotated[타입, 메타데이터]` — Python 표준(`typing`) 문법. "타입은 `list[str]`이고, 추가 정보(`operator.add`)도 같이 붙여둔다"는 뜻
- 타입(`list[str]`) 자체는 그대로, `operator.add`는 **LangGraph가 읽어가는 라벨** — Python 자체는 이 라벨을 무시하고 넘어가지만, LangGraph는 State 클래스를 읽을 때 이 라벨을 보고 reducer로 해석
- `operator.add` = `+` 연산자를 함수 형태로 만든 것 (`operator.add(a, b)` == `a + b`). 리스트에 적용하면 이어붙이기

---

## Edge: Control Flow (Serial / Parallel / Conditional)

| 종류                                       | 구조                                     | 특징                                                                      |
| ------------------------------------------ | ---------------------------------------- | ------------------------------------------------------------------------- |
| **Serial** (Lab 1)                         | `a → b → c`                              | 한 번에 하나씩 순차 실행. RentWise Phase 1 구조                           |
| **Parallel** (Lab 2)                       | `a → b`, `a → c` (한 노드에서 여러 edge) | 병렬로 동시 실행. `add_edge`를 같은 시작 노드에서 여러 번 호출하면 생성됨 |
| **Conditional** (다음 랩 예정)             | 점선 화살표, 조건 함수로 분기            | 실행 시점에 조건에 따라 어느 노드로 갈지 결정 (아직 미학습)               |
| **Map-Reduce** (Conditional의 특수 케이스) | 동적 개수의 브랜치 생성 후 합류          | 미리 개수를 못 박지 않고 데이터에 따라 가변 (아직 미학습)                 |

**Superstep**: 그래프 실행의 한 "단계" 단위. 병렬로 여러 노드가 동시에 실행되면, 그 노드들 전체가 하나의 superstep. 다음 노드는 이전 superstep의 모든 노드가 끝나야 실행됨 (join 지점에서 대기)

**Defer (경로 길이가 다를 때)**: 병렬 브랜치의 길이가 서로 다르면(한쪽은 1단계, 다른 쪽은 2단계), 짧은 쪽이 먼저 도착해서 데이터 불일치가 생길 수 있음 → 짧은 경로 노드에 `defer` 옵션을 걸어서 긴 경로와 같은 superstep에 도착하도록 강제 가능

---

## 핵심 원칙: Control은 Edge를 따르지만, Data는 따르지 않는다

> "Edges define control flow, but they do not control the data that nodes have access to."

- Edge는 **"누가 언제 실행되는가"**만 결정
- State는 그래프 전체가 공유하는 저장소라서, **이전 superstep에서 쓰인 값은 edge 연결 여부와 무관하게 이후 모든 노드가 볼 수 있음**
- 실제 확인: `bb`는 `add_edge("b", "bb")`로 **b와만** 직접 연결됐지만, 실행 시점엔 `c`가 쓴 값도 이미 State에 반영되어 있어 `bb`가 그걸 그대로 봄 (같은 superstep에 b, c가 동시 실행됐기 때문)

**RentWise 시사점**: Phase 2에서 에이전트 3개를 병렬 실행할 때, 스코어링 노드는 "edge로 직접 연결된 에이전트"뿐 아니라 **그 시점까지 끝난 모든 에이전트의 State**를 볼 수 있음. 단, 경로 길이가 다르면 일부 데이터가 아직 안 쓰인 채로 스코어링이 먼저 돌 위험 있음 → defer로 동기화 필요.

---

## LangGraph 병렬 실행 예제 (Lab 2: Parallel Execution)

```python
import operator
from typing import Annotated, TypedDict
from langgraph.graph import END, START, StateGraph

# 1. State 정의 (reducer 추가)
class State(TypedDict):
    nlist: Annotated[list[str], operator.add]

# 2. Node 정의 — 각자 자기 라벨만 리턴 (delta)
def node_a(state: State) -> State:
    return State(nlist=["A"])
def node_b(state: State) -> State:
    return State(nlist=["B"])
def node_c(state: State) -> State:
    return State(nlist=["C"])
def node_bb(state: State) -> State:
    return State(nlist=["BB"])
def node_cc(state: State) -> State:
    return State(nlist=["CC"])
def node_d(state: State) -> State:
    return State(nlist=["D"])

# 3. 그래프 조립 — 다이아몬드 구조
builder = StateGraph(State)
builder.add_node("a", node_a)
builder.add_node("b", node_b)
builder.add_node("c", node_c)
builder.add_node("bb", node_bb)
builder.add_node("cc", node_cc)
builder.add_node("d", node_d)

builder.add_edge(START, "a")
builder.add_edge("a", "b")
builder.add_edge("a", "c")      # a에서 두 개의 edge → 병렬 분기
builder.add_edge("b", "bb")
builder.add_edge("c", "cc")
builder.add_edge("bb", "d")
builder.add_edge("cc", "d")      # bb, cc → d로 수렴 (join)
builder.add_edge("d", END)

graph = builder.compile()

# 4. 실행
initial_state = State(nlist=["Initial String:"])
graph.invoke(initial_state)
# 결과: {'nlist': ['Initial String:', 'A', 'B', 'C', 'BB', 'CC', 'D']}
```

**실행 순서 확인 포인트**:

- `a` 실행 시점: 초기 State만 보임 (첫 실행이라 아무도 안 씀)
- `b`, `c`: 동시 실행(같은 superstep) — 서로 같은 State를 봄
- `bb`, `cc`: 다음 superstep — `b`와 `c`의 결과를 **둘 다** 봄 (edge로 직접 연결 안 된 쪽 결과까지 포함)
- `d`: `bb`, `cc` 둘 다 끝난 뒤 실행, 최종 병합 리스트 완성

---

## Lab 2 → RentWise Phase 2 매핑

| Lab 2                                       | RentWise Phase 2 (예상)                                                                    |
| ------------------------------------------- | ------------------------------------------------------------------------------------------ |
| `nlist: Annotated[list[str], operator.add]` | 예: `issues: Annotated[list[str], operator.add]` (여러 에이전트가 공통 이슈 리스트에 기여) |
| `a → b`, `a → c` (병렬 분기)                | `START → zillow`, `START → hpd`, `START → 311` (세 에이전트 병렬 실행)                     |
| `bb → d`, `cc → d` (join)                   | 세 에이전트 → `scoring` 노드로 수렴                                                        |
| Control ≠ Data 원리                         | 스코어링 노드가 edge로 직접 연결 안 된 에이전트 결과도 State로 접근 가능                   |
| Defer                                       | 에이전트별 처리 단계 수가 다를 경우, 스코어링 전에 모두 동기화되도록 지정 필요             |

---

## Grilling 대비 메모 (추가)

- **reducer가 왜 필요한가**: 병렬 실행 시 여러 노드가 같은 State 키를 동시에 쓰면 충돌 발생 — reducer로 병합 규칙을 명시적으로 정의해서 해결
- **Control flow vs Data 구분을 아는 것의 실전 가치**: 디버깅 시 "이 노드가 왜 예상 못한 데이터를 보고 있지?"라는 혼란을 방지하는 핵심 개념. 인터뷰에서 LangGraph 내부 동작 이해도를 보여줄 수 있는 포인트

---

## Conditional Edge — 두 가지 구현 방식

Static edge(Serial/Parallel)는 항상 정해진 경로만 갔지만, Conditional Edge는 **실행 중에 State를 보고 다음 노드를 동적으로 결정**함. 구현 방식은 두 가지, 결과는 동일:

|                          | 방식 A: `add_conditional_edges` + 별도 함수            | 방식 B: `Command` (node가 직접 라우팅) |
| ------------------------ | ------------------------------------------------------ | -------------------------------------- |
| 라우팅 로직 위치         | 별도 함수 (`conditional_edge`)                         | 노드 함수(`node_a`) 안에 통합          |
| 노드 자체가 하는 일      | 아무것도 안 함 (State 안 건드림)                       | State 업데이트 + 라우팅 동시 처리      |
| 그래프 조립 시 필요한 줄 | `builder.add_conditional_edges("a", conditional_edge)` | 없음 (`node_a`가 스스로 처리하므로)    |

**중요: 두 방식을 절대 동시에 켜면 안 됨.** `node_a`가 이미 `Command`로 라우팅하고 있는데 `add_conditional_edges`까지 걸면, `a`에서 나가는 경로가 이중으로 정의되어 그래프 렌더링 시 `TypeError`(`'<' not supported between NoneType and str`) 발생. 이 둘은 "고르는" 것이지 "합치는" 게 아님.

---

### 방식 A: `add_conditional_edges`

```python
def node_a(state: State):
    return   # 아무 업데이트도 안 함 — State는 그대로 통과됨

def conditional_edge(state: State) -> Literal["b", "c", END]:
    select = state["nlist"][-1]
    if select == "b": return "b"
    elif select == "c": return "c"
    elif select == "q": return END
    else: return END

builder.add_conditional_edges("a", conditional_edge)
```

**`node_a`가 빈 함수인 이유**: `node_a`는 데이터 처리가 아니라, 그래프 구조상 "conditional_edge가 실행될 지점"을 만들어주는 역할만 함. `return`만 있고 리턴값이 없으면(=`None`), State는 아무 변화 없이 그대로 다음 단계로 넘어감 — 릴레이로 문서를 넘길 때 아무것도 안 적고 그냥 넘기는 것과 같은 개념.

**`conditional_edge`는 노드가 아님**: `add_node()`로 등록되지 않았기 때문에 그래프상 노드 취급 안 됨. `add_conditional_edges("a", conditional_edge)`로 "a 다음엔 이 함수의 판단을 따르라"고 **등록**만 해두는 것.

**호출 주체는 우리가 아니라 LangGraph**: `conditional_edge(state)`라는 코드를 우리가 직접 쓴 적은 없음. `add_conditional_edges`로 등록해두면, 그래프 실행 중 `a` 노드 처리가 끝나는 시점에 **LangGraph 프레임워크가 자동으로 이 함수를 호출**하고, 그때 현재 State를 인자로 넘겨줌.

---

### 방식 B: `Command`

```python
def node_a(state: State) -> Command[Literal["b", "c", END]]:
    select = state["nlist"][-1]
    if select == "b": next_node = "b"
    elif select == "c": next_node = "c"
    elif select == "q": next_node = END
    else: next_node = END
    return Command(
        update = State(nlist = [select]),
        goto = [next_node]
    )
```

**`Command`란**: LangGraph가 제공하는 클래스. State 업데이트와 "다음 노드 지정"을 하나의 객체로 묶어서 리턴할 수 있게 해줌.

**`update`, `goto`는 우리가 만든 이름이 아님**: `Command` 클래스가 미리 정의해둔 매개변수. `State(nlist=...)`에서 `nlist`는 우리가 직접 정한 필드명이지만, `Command`의 `update`/`goto`는 **라이브러리 쪽에서 이미 이름이 고정된 것** — `Command`를 쓰려면 이 이름 그대로 값을 넣어야 함.

- `update=` → State를 이렇게 바꿔라
- `goto=` → 다음엔 여기로 가라 (노드 이름 리스트)

**`-> Command[Literal["b", "c", END]]`의 의미**: `Command[...]` 대괄호는 "이 Command가 갈 수 있는 목적지가 b/c/END로 제한된다"는 타입 정보. **그래프 실행 자체엔 영향 없음** — 오직 `draw_mermaid_png()`가 그래프를 시각화할 때 edge를 정확히 그리기 위한 용도. 지워도 그래프는 똑같이 작동하지만 그림만 부정확해짐.

**`goto`의 특이사항**:

- 문자열이 실제 노드 이름과 일치하는지는 **런타임에만 체크됨** (코드 작성 시점엔 오타가 있어도 에러 안 남, 실행해야 드러남)
- `goto`는 리스트를 받을 수 있어서 **여러 노드를 동시에 지정하면 병렬 실행도 가능** (Lab 2의 병렬 실행과 연결되는 지점)

---

### `select`와 `input()`으로 받은 `user`의 관계

헷갈리기 쉬운 부분이라 정리:

```python
user = input('b, c, or q to quit: ')   # ① 사용자가 "b" 입력
input_state = State(nlist = [user])       # ② {"nlist": ["b"]}
result = graph.invoke(input_state)          # ③ 그래프에 주입
```

`invoke()`에 넣은 `input_state`가 그래프의 시작 State가 되어 `START → a`로 전달됨. `node_a`(방식 A의 빈 버전이든, 방식 B의 Command 버전이든)를 거치면서 `state["nlist"][-1]`로 그 값을 다시 꺼내는 게 `select`.

**`select`와 `user`는 같은 값**이고, 다만 거쳐온 경로가 다름:

user (input()으로 직접 받음)
→ State(nlist=[user])로 포장
→ graph.invoke()로 그래프에 주입
→ 노드/조건함수 안에서 state["nlist"][-1]로 다시 꺼냄
→ 그게 select

`input()`은 "사용자 → Python 변수"로 값을 가져오는 통로, `state["nlist"][-1]`은 "State 딕셔너리 → 함수 내부"로 같은 값을 다시 꺼내는 통로. 완전히 별개의 값이 아니라 **같은 값이 다른 시점에 다른 형태로 다뤄지는 것**.

---

### 디버깅 체크리스트 (실습 중 겪은 에러 기록)

**증상**: `graph.get_graph().draw_mermaid_png()` 호출 시 `TypeError: '<' not supported between instances of 'NoneType' and 'str'`

**원인 1 — 두 방식 동시 사용**: `node_a`가 Command로 이미 라우팅하는데 `add_conditional_edges`도 추가로 걸어서 `a`의 나가는 경로가 이중 정의됨.

**원인 2 — 커널에 이전 버전이 남아있음**: 셀 코드를 주석 처리하고 재실행해도, **Jupyter 커널은 이전에 실행됐던 함수 정의를 메모리에 그대로 유지**함. "코드를 지웠다"가 "메모리에서도 사라졌다"를 의미하지 않음. 함수 정의를 실질적으로 바꾸려면:

1. 셀 코드 자체를 원하는 버전으로 고쳐 쓰기 (주석 처리가 아니라)
2. 커널 재시작(`Kernel → Restart Kernel`)으로 메모리 초기화
3. 위에서부터 순서대로 다시 실행

**교훈**: 두 방식(A/B)을 전환하며 실습할 땐, 반드시 (1) `node_a` 정의 자체를 해당 방식에 맞게 고쳐 쓰고 (2) 그래프 조립 코드에서 안 쓰는 방식의 줄은 지우거나 주석 처리하고 (3) 헷갈리면 커널 재시작 후 처음부터 재실행하는 게 가장 확실함.

---

## Lab 3 → RentWise 연결

- Phase 1 확장 시나리오: "HPD API가 404를 리턴하면 → 311 조회로 스킵, 데이터가 있으면 → 정상적으로 HPD 분석 노드로" 같은 로직이 Conditional Edge 패턴
- 방식 선택 기준: 라우팅 로직이 단순하고 노드와 밀접하면 Command, 라우팅 로직을 여러 곳에서 재사용하거나 노드 로직과 분리해 테스트하고 싶으면 `add_conditional_edges` — RentWise 규모에서는 아직 어느 쪽이 유리한지 확정할 단계는 아니지만, 개념상 후자가 "관심사 분리" 원칙에 더 부합

---

## Memory / Checkpointer

지금까지 `graph.invoke()`를 부를 때마다 매번 새로운 State에서 시작했음. Memory는 **서로 다른 invoke 호출 사이에도 State가 이어지게** 만드는 기능.

**세 가지 계층 구조** (위에서 아래로):

| 개념           | 정의                                                                                         |
| -------------- | -------------------------------------------------------------------------------------------- |
| **State**      | 각 superstep 시작 시 노드에 공급되고, 끝날 때 업데이트되는 데이터 (Lab 1~3에서 이미 다룬 것) |
| **Checkpoint** | 매 스텝이 끝날 때마다 그 시점의 State를 저장한 **스냅샷**                                    |
| **Thread**     | 여러 Checkpoint를 시간순으로 모아놓은 것 = "이 세션의 전체 히스토리"                         |

**Checkpointer의 4가지 이점**:

- **Recover gracefully from failures** — 노드 실패 시 처음부터가 아니라 실패 지점부터 재개
- **Time travel** — 과거의 정상 시점으로 되감아서 그 지점부터 재시작 가능
- **Persistent state** — 그래프가 실행 중이 아닐 때도 State가 보존됨
- **Restore state at any step** — 중단된 실행을 정확히 멈춘 지점부터 재개 (human-in-the-loop과 연결)

**LangGraph 기본 제공 checkpointer 3종**: `InMemorySaver`(RAM, 가장 간단), `PostgresSaver`, `SQLiteSaver`(각각 해당 DB에 영구 저장). 이번 랩은 가장 단순한 `InMemorySaver` 사용.

---

## Memory 구현 코드 (Lab 4)

```python
from langgraph.checkpoint.memory import InMemorySaver

memory = InMemorySaver()                              # 실제 저장소 (인스턴스)
config = {"configurable": {"thread_id": "1"}}         # "어떤 세션을 쓸지" 지정하는 딕셔너리

graph = builder.compile(checkpointer=memory)          # 컴파일 시 checkpointer 등록
```

Lab 3 코드와의 **유일한 차이**: `invoke()` 호출 시 `config`를 같이 넘겨줌.

```python
result = graph.invoke(input_state, config)   # config 추가된 것 외엔 Lab 3과 동일
```

**동작 원리**: `thread_id`가 같으면 이전 State에 이어붙여짐, `thread_id`가 다르면 완전히 새로운 State에서 시작.

---

## 실습 중 발견한 함정: `memory`와 `config`는 역할이 다름

**증상**: `thread_id`를 `"1"` → `"2"` → 다시 `"1"`로 바꿔가며 실습했는데, `"1"`로 돌아와도 이전 기록이 안 남아있고 매번 새로 시작하는 것처럼 보임.

**원인**: `config` 셀 전체를 다시 실행하면서 `memory = InMemorySaver()` 줄까지 같이 재실행됨. 이 줄이 재실행되는 순간, **기존 기록을 담고 있던 저장소 자체가 통째로 새것(텅 빈 것)으로 교체**됨.

**핵심 구분**:
| | 역할 | 재실행 시 |
|---|---|---|
| `memory = InMemorySaver()` | **실제 저장소 그 자체** (모든 thread의 기록이 여기 담김) | 재실행하면 저장소 전체가 초기화됨 — **노트북에서 딱 한 번만 실행해야 함** |
| `config = {...}` | 그냥 "이번엔 어떤 thread_id를 쓸지" 알려주는 딕셔너리 | 자유롭게 여러 번 바꿔도 됨 — 오히려 이걸 바꿔야 세션 전환이 됨 |

**올바른 실습 순서**: `memory`와 `graph = builder.compile(...)`는 최초 한 번만 실행하고, 이후 `thread_id`를 바꿀 땐 **`config` 정의 줄만 따로 떼서 그 줄만** 재실행할 것.

---

## Try Next 검증 결과

1. 같은 `thread_id`로 반복 실행 → 값이 누적됨 ✓
2. `thread_id`를 다른 값으로 바꿈 → 완전히 새로운 State에서 시작 ✓
3. 이전 `thread_id`로 복귀 → 기존 기록이 그대로 남아있음 ✓ (persistent state 실증)

---

## Lab 4 → RentWise 연결

concepts.md 상단 "Grilling 대비 메모"의 "왜 LangGraph인가" 답변(Checkpointing으로 실패 지점부터 재시도 가능)이 이번 랩에서 실제 코드로 증명됨.

- Zillow(스텝1) → HPD(스텝2) → 311(스텝3) 각 단계가 끝날 때마다 checkpoint 생성
- HPD 단계에서 실패해도 Zillow 체크포인트는 살아있으므로, 처음부터가 아니라 HPD부터 재시도 가능
- `thread_id`는 RentWise에서 "사용자별 조회 세션"에 대응시킬 수 있음 — 예: 사용자가 여러 주소를 연달아 조회할 때 각 조회를 별도 `thread_id`로 분리하거나, 하나의 대화 세션 안에서 여러 주소 히스토리를 누적시키는 데 활용 가능
- Phase 1은 `InMemorySaver`로 충분(휘발성 무방, 단일 세션 테스트 목적). Phase 2에서 RDS 도입 시 `PostgresSaver`로 전환하면 서버 재시작에도 기록이 영구 보존됨 — 이게 "왜 Phase 2에 PostgreSQL을 넣었는가"에 대한 추가 근거로 쓸 수 있음

---

## Interrupt / Human-in-the-loop

지금까지는 그래프가 한 번 실행되면 끝까지 자동으로 진행됐음. Interrupt는 **실행 도중 특정 노드에서 "사람 확인이 필요하다"고 판단하면 그 자리에서 그래프를 완전히 정지시키고, 사람 응답이 오면 그 지점부터 재개**하는 기능. 대표 사례: 도구 실행 전 승인, DB 쓰기 전 sign-off.

Checkpointer(Lab 4)가 전제 조건 — 정지 시점의 state를 저장해뒀다가 복원하는 게 checkpointer 역할.

### 코드 패턴

```python
from langgraph.types import Command, interrupt

def node_a(state: State) -> Command[Literal["b", "c", END]]:
    ...
    else:  # illegal value
        admin = interrupt(f"Unexpected input '{select}'")
        if admin == "continue":
            next_node = "b"
        else:
            next_node = END
    return Command(update=..., goto=next_node)
```

```python
while True:
    result = graph.invoke(input_state, config)

    if '__interrupt__' in result:
        msg = result['__interrupt__'][-1].value
        human = input(f"\n{msg}: ")
        result = graph.invoke(Command(resume=human), config)
```

- `interrupt()` 호출 시 그래프 정지 → `result['__interrupt__']`에 메시지(`Interrupt.value`)와 id 담겨 리턴
- `Command(resume=값)`으로 재호출 시 값이 공급되고 실행 재개 — 반드시 **같은 config(같은 thread_id)**로 호출해야 checkpointer가 정지 상태를 찾음

### 핵심 동작: 노드는 항상 처음부터 재시작됨

resume 시 `interrupt()` 호출 지점부터 이어지는 게 아니라 **노드 함수 전체가 처음부터 재실행**됨. 노드가 클 경우 중간 지점의 모든 intermediate state를 살려두는 비용을 피하기 위한 설계.

재실행돼도 같은 interrupt에 다시 멈추지 않는 이유: LangGraph가 응답을 자동으로 checkpoint하고, 이미 답변된 interrupt를 다시 만나면 저장된 값을 즉시 공급함(스킵). 그래서 한 노드 안에 interrupt가 여러 개 있어도 LangGraph가 순서를 추적함.

**주의**: `interrupt()` 이전 코드는 resume마다 매번 재실행되므로, 부작용 큰 코드(DB 쓰기 등)는 interrupt 이전에 두지 않는 게 안전.

### 기타

- `__interrupt__` 값이 리스트인 이유: 병렬 노드가 각각 interrupt를 걸면 여러 개가 한 리스트에 담길 수 있음

## Lab 5 → RentWise 연결

- Phase 1 스코프에서는 우선순위 낮음 — Zillow→HPD→311이 자동 순차 실행이라 사람 승인 지점이 아직 없음
- 향후 확장 가능 지점: 매물 데이터가 이상치로 판단될 때 "사람 확인 후 진행" 같은 검수 단계에 적용 가능 (Phase 2 이후 고려)
- Lab 4의 checkpointer가 Lab 5의 정지/재개 메커니즘의 기반이라는 점에서 두 랩은 같은 인프라를 공유 — RentWise에서 checkpointer를 도입하면 향후 interrupt 기능도 자연스럽게 확장 가능

---

## Lab 6: Email Agent (Build A Workflow) — 종합 실습

Lab 1~5의 모든 개념(State, Node, Edge, 병렬 실행, Conditional routing via Command, Checkpointer, Interrupt)을 하나의 프로덕션 스타일 워크플로우로 조합한 캡스톤 랩.

### 시나리오

고객 이메일 수신 → LLM이 분류 → (문서 검색 + 버그 티켓 생성 병렬) → LLM이 답장 초안 작성 → 긴급도/의도에 따라 사람 검토 필요 여부 자동 판단 → (필요시 interrupt로 정지 후 승인/거부) → 발송

### 그래프 구조

start → read_email → classify_intent
├→ bug_tracking ─┐
└→ search_documentation ─┤
write_response
├→ human_review ─┬→ send_reply → end
│ └→ end (거부 시)
└→ send_reply → end (검토 불필요 시)

### State 설계 — 노드 다이어그램 기준으로 설계

```python
class EmailClassification(TypedDict):
    intent: Literal["question", "bug", "billing", "feature", "complex"]
    urgency: Literal["low", "medium", "high", "critical"]
    topic: str
    summary: str

class EmailAgentState(TypedDict):
    email_content: str          # 입력값
    sender_email: str           # 입력값
    email_id: str                # 입력값
    classification: EmailClassification | None   # classify_intent가 채움
    ticket_id: str | None                          # bug_tracking이 채움
    search_results: list[str] | None               # search_documentation이 채움
    customer_history: dict | None                  # (미사용 노드, 향후 확장용)
    draft_response: str | None                     # write_response가 채움
```

**설계 원칙**: 노드 다이어그램을 보면서 "이 노드가 뭘 만들어내야 다음 노드가 쓸 수 있나"를 하나씩 확인하며 필드 추가. 복잡한 결과(분류 결과 4개 필드)는 별도 TypedDict로 분리. 이 에이전트는 이메일 한 통 처리로 스코프가 한정돼서(이전 이메일 기록 누적 불필요) `Annotated`/커스텀 reducer 불필요 — 기본 reducer(덮어쓰기)로 충분.

### 핵심 패턴 1 — 구조화 출력으로 LLM 응답 형식 강제

```python
structured_llm = llm.with_structured_output(EmailClassification)
classification = structured_llm.invoke(prompt)   # 곧바로 dict로 리턴
```

스키마가 형식은 강제하지만 내용 품질은 프롬프트가 좌우함 → 필드를 프롬프트에도 명시하는 게 실무 관행.

### 핵심 패턴 2 — 에러를 크래시 대신 데이터로 전달

```python
try:
    search_results = [...]
except SearchAPIError as e:
    search_results = [f"Search temporarily unavailable: {str(e)}"]
```

에이전트는 오래 실행될 수 있으므로 에러로 죽으면 안 됨. 에러를 문자열로 캡처해 다음 노드(LLM)에 넘기면, LLM이 실패를 인지한 채로 대응 가능. RentWise의 Zillow/HPD/311 API 호출에 동일 패턴 적용 예정.

### 핵심 패턴 3 — 디폴트값은 "명확한 플레이스홀더"로

```python
classification.get('intent', 'unkown')   # 빈 문자열(") 대신 "unknown"
```

빈 문자열은 LLM이 "값이 없다"를 인식 못 함 → 예측 불가능한 결과로 이어짐. 명확한 기본값이 에이전트를 resilient하게 만듦.

### 핵심 패턴 4 — Command로 조건부 라우팅 + 사람 판단이 필요한 기준

```python
needs_review = (
    classification.get('urgency') in ['high', 'critical'] or
    classification.get('intent') == 'complex'
)
```

"긴급해서"뿐 아니라 "LLM이 카테고리 분류에 확신 못 해서"(`complex`)도 human review 트리거. Confidence 낮은 케이스를 사람 검토로 보내는 패턴 — RentWise에서 GPT 판정 확신도 낮을 때 적용 고려.

### 핵심 패턴 5 — Interrupt 페이로드는 "의사결정에 필요한 것만"

```python
human_decision = interrupt({
    "email_id": ..., "original_email": ..., "draft_response": ...,
    "urgency": ..., "intent": ..., "action": "..."
})
```

state 전체를 던지지 않고 사람이 판단하는 데 필요한 필드만 선별. interrupt는 노드 맨 앞에 배치(재실행 시 앞쪽 코드 재실행 최소화).

### LangGraph Studio로 실행 (노트북 대신 UI 데모)

```bash
cd ~/lca-langgraph-essentials/python
cp .env ./studio/.
cd studio
uv run langgraph dev
```

- `langgraph.json`이 `email-agent.py:builder`(컴파일 전 StateGraph)를 가리킴 — Studio가 컴파일+checkpointing 자체 관리
- 브라우저에서 LangSmith 로그인 → Studio UI 진입
- Input 폼에 `email_content`/`sender_email`/`email_id` 입력 → Submit
- interrupt 도달 시 자동 정지, 화면에 검토 카드 표시
- **Resume 값은 반드시 JSON 모드로 입력**: `{"approved": true}` — Text 모드로 넣으면 `AttributeError: 'str' object has no attribute 'get'` 발생 (실제로 겪은 에러)
- Thread 타임라인에서 각 노드의 입출력(`ticket_id`, `search_results`, `draft_response` 등)을 노드별로 확인 가능 — 병렬 노드(`search_documentation`+`bug_tracking`)가 같은 타임스탬프에 나란히 실행된 것도 시각적으로 확인됨

### 실전 테스트 완료

단일 이메일(urgent billing) → human_review 정지 → JSON resume 승인 → send_reply까지 end-to-end 성공. `__start__`부터 `__end__`까지 전체 경로, 노드별 산출물(ticket_id는 실제 UUID, draft_response는 LLM이 생성한 실제 텍스트) 확인 완료.
