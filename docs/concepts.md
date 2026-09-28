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

## Zillow Agent 구현 중 배운 개념

- **state의 정체**: 함수가 받는 파라미터 이름일 뿐인 딕셔너리. state["키"]로 값 꺼냄. 실행 중간 시점엔 아직 안 채워진 필드가 있을 수 있음 (해당 노드가 아직 안 돌았으니까).
- **딕셔너리 키에 따옴표 필요한 이유**: 따옴표 없으면 "변수 이름"으로 해석됨. "address"처럼 써야 "글자 자체"로 인식.
- **노드 리턴 컨벤션**: 각 노드는 자기가 새로 채운 필드만 담은 부분 딕셔너리를 리턴 → LangGraph가 기존 State와 자동 병합. 전체 State를 다시 안 담아도 됨.
- **class vs def**: 타입(TypedDict) 정의는 class, 함수 정의는 def.
- **with_structured_output(스키마)**: GPT가 정해진 필드만 가진 dict로 응답하도록 강제. Lab 6 EmailClassification 패턴을 VerdictExplanation에 그대로 적용.
- **리스트 컴프리헨션**: [comp["rent"] for comp in state["comps"]]는 for loop를 한 줄로 압축한 것.

## Zillow Agent — RentCast API 연동 (실습 기록)

### `.env` → 환경변수 → 코드로 이어지는 흐름

```python
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("RENTCAST_API_KEY")
```

- `.env` 파일 자체는 그냥 텍스트 파일(`키=값`). 파이썬이 자동으로 읽지 않음
- `load_dotenv()`: `.env` 내용을 환경변수 공간에 등록 (비유: 봉투를 뜯어 책상 위에 꺼내놓는 행위)
- `os.getenv("이름")`: 환경변수에서 값을 찾아 리턴, 없으면 `None`
- 둘은 항상 세트 — `load_dotenv()` 없이 `os.getenv()`만 부르면 아무것도 못 찾음
- `load_dotenv()`는 함수 안이 아니라 **파일 최상단에서 한 번만** 호출 (여러 함수가 재사용하므로)

---

### OpenAI 전용 클라이언트 vs RentCast raw request — 같은 목적, 다른 방식

|           | `chatbot.py` (OpenAI)                            | Zillow agent (RentCast)                      |
| --------- | ------------------------------------------------ | -------------------------------------------- |
| 인증 처리 | 전용 클래스(`OpenAI(api_key=...)`)가 대신 처리   | 전용 SDK 없음 → `headers`에 직접 넣어야 함   |
| 호출 방식 | `client.chat.completions.create(...)`            | `requests.get(url, headers=..., params=...)` |
| 응답 형태 | 이미 파싱된 객체 (`.choices[0].message.content`) | 원시 응답 → `.json()`으로 직접 변환 필요     |

**실수 사례**: `RentCast(api_key=...)`라는, 존재하지 않는 클래스를 상상해서 쓴 적 있음. `chatbot.py` 패턴을 그대로 복붙하려 했지만, RentCast는 전용 SDK가 없어서 애초에 그런 클래스가 없었음 → 라이브러리가 "무엇을 대신 해주는지"부터 확인하는 습관 필요.

---

### `requests`로 외부 API 호출하기 — 세 가지 재료

```python
url = RENTCAST_RENT_ESTIMATE_URL
params = {"address": state["address"], "bedrooms": state["bedrooms"]}
headers = {"X-Api-Key": api_key}

response = requests.get(url, params=params, headers=headers)
response.raise_for_status()
data = response.json()
```

- **`params`**: URL 뒤에 붙는 검색 조건(`?키=값&키=값`). 브라우저 검색창의 `?q=검색어`와 같은 개념. 딕셔너리로 넘기면 `requests`가 URL 형식으로 자동 조합
- **`headers`**: "누가 요청하는지"를 증명하는 인증 정보. API 키는 보안상 URL(`params`)이 아니라 `headers`에 넣는 경우가 많음 (RentCast는 `X-Api-Key`)
- **`response.json()`**: 원시 응답을 파이썬 딕셔너리로 변환. OpenAI처럼 미리 파싱된 객체를 주지 않으므로 직접 변환 필요
- **`response.raise_for_status()`**: 상태가 4xx/5xx면 그 자리에서 `HTTPError`를 스스로 던짐 — 없으면 에러 응답도 조용히 넘어가서 디버깅이 어려워짐

---

### `try/except`로 API 실패 대비 — fallback 패턴

```python
FALLBACK_COMPS: list[CompListing] = [...]

def fetch_comps(state: ZillowAgentState) -> ZillowAgentState:
    try:
        ...
        response.raise_for_status()
        data = response.json()
        raw_comps = data.get("comparables", [])

        comps = []
        for c in raw_comps:
            comp = {"address": c["formattedAddress"], "rent": c["price"], "bedrooms": c["bedrooms"]}
            comps.append(comp)

    except requests.exceptions.RequestException as e:
        print(f"API call failed, using fallback: {e}")
        return ZillowAgentState(comps=fallback_comps)

    return ZillowAgentState(comps=comps)
```

- 문법은 `if`/`for`와 동일한 패턴: 콜론(`:`) + 들여쓰기. `{}` 안 씀
- `RequestException`은 `HTTPError`를 포함하는 더 넓은 범위의 예외 — 인증 에러부터 네트워크 단절까지 폭넓게 커버. 반대로 `HTTPError`는 "서버가 4xx/5xx로 응답한 경우"만 잡는 좁은 범위
- `as e`로 예외 객체를 변수에 담아야 `print(f"...{e}")`로 실제 에러 내용 확인 가능. `as e` 없이 `e`를 쓰면 `NameError`
- **분기 설계**: `try`가 끝까지 성공하면 함수 마지막의 `return`, 중간에 실패하면 `except` 안에서 조기 `return` — 함수 전체를 관통하는 하나의 `return`으로 두 경로를 다 처리하려 하면 로직이 꼬임

**실전 검증 (추측 대신 로그로 확인)**: "403일 것이다"라고 짐작만 하고 넘어갈 뻔했으나, `except` 안에 `print(e)`를 넣어 실제 실행해보니 **401 Unauthorized**였음. 짐작이 항상 맞는 건 아니므로, `except` 블록에 로그를 남겨서 실제로 확인하는 습관이 중요.

---

### 디버깅 체크리스트 (직접 겪은 실수들)

**증상 1**: 클래스 이름을 변수명으로 재사용

```python
CompListing = {"address": ..., ...}   # ✗ 클래스 정의 자체를 덮어씀
```

→ 다른 변수명(`comp` 등) 사용해야 함

**증상 2**: 딕셔너리 키에 따옴표 누락

```python
{address: c.formattedAddress}   # ✗ address를 "변수 이름"으로 해석
{"address": c["formattedAddress"]}   # ✓
```

**증상 3**: JSON 파싱 결과를 객체처럼 접근

```python
c.formattedAddress   # ✗ — c는 클래스 인스턴스가 아니라 딕셔너리
c["formattedAddress"]   # ✓
```

**증상 4**: 리스트에 `.add()` 사용

```python
comps.add(comp)   # ✗ .add()는 set 전용 메서드
comps.append(comp)   # ✓
```

**증상 5**: `except`에 `as e` 없이 `e` 사용

```python
except requests.exceptions.RequestException:
    print(f"...{e}")   # ✗ NameError: name 'e' is not defined
except requests.exceptions.RequestException as e:
    print(f"...{e}")   # ✓
```

**교훈**: 좌변(우리가 지을 키 이름)과 우변(원본 데이터에서 꺼내는 키)은 독립적으로 정할 수 있음. 예: `"rent": c["price"]` — RentCast는 매매든 임대든 가격 필드를 `price`로 통일해서 줌.

---

### RentCast `/avm/rent/long-term` 스펙 요약

| 항목                 | 내용                                                                                            |
| -------------------- | ----------------------------------------------------------------------------------------------- |
| 요청 파라미터        | `address`, `bedrooms`, (선택) `bathrooms`, `squareFootage`, `maxRadius`, `daysOld`, `compCount` |
| 응답 최상위          | `rent`, `rentRangeLow`, `rentRangeHigh`, `subjectProperty`, `comparables`                       |
| `comparables[]` 필드 | `formattedAddress`, `price`(임대료), `bedrooms`, `distance`, `correlation` 등                   |
| `CompListing` 매핑   | `address` ← `formattedAddress` / `rent` ← `price` / `bedrooms` ← `bedrooms`                     |
| 무료 티어            | 월 50건, **카드 등록 필수** (완전 무료 아님 — 결제 화면까지 직접 확인해야 확실히 앎)            |

---

## Grilling 대비 메모 (추가)

- **왜 fallback 구조를 넣었나**: 외부 API는 네트워크 문제, 인증 실패, rate limit 등으로 언제든 실패할 수 있음. 에이전트가 그 자리에서 죽지 않고 안전하게 계속 동작하도록 설계 — Lab 6의 "에러를 크래시 대신 데이터로 전달" 패턴과 동일한 철학
- **왜 `RequestException`(넓은 범위)을 골랐나**: 지금 당장은 인증 에러(401/403)만 예상되지만, 실제 배포 환경에서는 네트워크 단절, 타임아웃 등 다양한 실패 모드가 있을 수 있어 더 넓은 예외 클래스로 방어
- **RentCast를 실제로 구독하지 않고도 코드를 완성할 수 있었던 이유**: `try`/`except` 구조 덕분에 API 키 없이도 fallback 경로로 전체 파이프라인(`fetch_comps → compute_stats → explain_verdict`)을 끝까지 검증 가능했음 — 구독 여부와 코드 완성도를 분리해서 진행한 설계 판단

---

## compute_stats 점수 계산식 상세 근거 (HPD)

### violation_score

```
violation_score = Σ [ (class_weight × status_weight) + rentimpairing_bonus ]
    class_weight:   C=3, B=2, A=1, I=0      # 위반 등급이 심각할수록 가중치 큼
    status_weight:  Open=1.5, Close=1.0     # 아직 안 고친 위반에 1.5배 가중
    rentimpairing_bonus: True → +2, False → +0   # 법적으로 임대료 지급거부 근거가 될 정도면 추가 가산
```

- `class_weight`와 `status_weight`는 곱셈 관계(같은 위반이 심각하면서 동시에 안 고쳐졌으면 배로 불리해짐), `rentimpairing_bonus`는 덧셈(별도 축이라 곱하면 과도하게 부풀려짐 — 처음엔 곱셈으로 검토했다가 덧셈으로 수정).

### enforcement_score

```
enforcement_score = Σ [ (1 × active_weight) + amount_bonus ]
    active_weight:  True → 1.5, False → 1.0
    amount_bonus (Charges 전용, OMOAwardAmount 실측 분포 기반):
        $0~$500        → +0.5   (하위 ~58%)
        $500~$5,000    → +1.5   (중간 ~38%)
        $5,000~$50,000 → +2.5   (상위 ~4%)
        $50,000 초과    → +4    (상위 ~0.4%)
        None           → 0
    is_landlord_fault == False인 레코드는 0점 (예: "Duplicate OMO", "Vacant Land")
```

**금액 구간을 실측 기반으로 잡은 이유**: 처음 감으로 잡은 구간($5K/$50K 기준)은 실제 분포(중앙값 $384, 90th percentile $2,700)와 완전히 안 맞았음. `OMOAwardAmount` 컬럼을 pandas로 직접 분석(`describe()`, `quantile()`)해서 실제 분포에 맞는 4구간(회원 건수: 294,286 / 194,494 / 21,688 / 1,958)으로 재조정.

### 소스별 is_active 판단 기준

```
AEP:        CURRENT_STATUS == "Active"
Charges:    항상 False
Litigation: CaseStatus == "PENDING"
Order:      RESCIND DATE가 비어있음
```

**Charges가 항상 False인 이유**: `OMOStatusReason` 필드가 공식적으로 "이 OMO가 **종료된** 사유"라고 정의됨. 즉 이 데이터셋은 애초에 종료된 케이스만 기록하는 구조라, "진행 중"이라는 상태 자체가 존재하지 않음. Litigation(`PENDING`/`CLOSED`가 실제로 공존)과 근본적으로 다른 데이터 성격.

### severity_label 임계값 산출

건물 174,370개(Violation Files는 InspectionDate 2025-09-01 이후로 필터링, 약 92.6만 행 / AEP·Charges·Litigation·Orders는 전체 데이터셋) 대상으로 로컬 pandas 분석.

```
분포: 중앙값 2, 75th 9.5, 90th 45, 95th 100.5, 99th 323, 최댓값 3451.5
0점(완전 클린) 건물: 17,202개 (9.9%)

기준:
    5 미만    → "good"     (사소한 위반 1~2건 수준)
    45 미만   → "caution"
    45 이상   → "danger"   (90th percentile = 상위 약 10%)
```

`5`라는 경계값이 계산식과 우연히 맞아떨어지는 지점: Class B(가중치2)+Open(1.5배)=3점에 rentimpairing 보너스(+2)를 더하면 정확히 5점 — "위험 등급 위반이 열려있으면서 법적으로도 심각"한 최소 조건과 일치.

---

## Pandas: 비즈니스 로직 확정 전 실제 데이터 검증하기

- **왜 필요한가**: "감으로" 잡은 임계값이나 구간 경계는 실제 데이터 분포와 비교하기 전까지는 완전히 틀렸을 수 있음. 오늘 실제로 두 번이나 자릿수가 다를 정도로 틀렸던 사례:
  - Charges 금액 구간을 $5K/$50K로 추측했지만, 실제 분포는 중앙값 $384, 90th percentile이 겨우 $2,700
  - 파싱 버그 때문에 관측된 최댓값이 $999.99로 보였지만 실제 최댓값은 $7,346,315 (아래 참고)
- **사용한 패턴**: 구간 경계나 가중치를 정하기 전에 `df[col].describe()` + `df[col].quantile([0.25, 0.5, 0.75, 0.9, 0.99])`로 컬럼의 실제 분포 모양부터 확인.

## `pd.to_numeric(..., errors="coerce")` — 쉼표 포함 숫자의 함정

```python
df[col] = pd.to_numeric(df[col], errors="coerce")
```

- `errors="coerce"`: 숫자로 변환 안 되는 값은 에러를 내는 대신 `NaN`으로 바뀜 — 일부 값이 이상해도 나머지는 계속 처리 가능하게 해줌.
- **함정**: `"1,200"`(천단위 구분 쉼표가 붙은 문자열)은 `pd.to_numeric` 입장에서 유효한 숫자가 아님 — 에러 없이 조용히 `NaN`으로 바뀜. 컬럼의 약 25%가 `NaN`이 됐다면, 그냥 "정상 데이터가 이만큼"이라고 넘기지 말고 **왜** 이렇게 됐는지 확인해야 함.
- **해결**: 변환 전에 서식 문자 제거
  ```python
  df[col] = df[col].astype(str).str.replace(",", "", regex=False)
  df[col] = pd.to_numeric(df[col], errors="coerce")
  ```
- **교훈**: `describe()` 결과가 이상하리만치 깔끔해 보이면(예: 최댓값이 딱 `999.99`로 끝남) 그 자체가 단서임 — 실제 데이터가 우연히 딱 떨어지는 숫자에서 끊기는 경우는 드묾. 이 패턴이 "진짜 데이터 한계"가 아니라 파싱 버그를 가리키는 신호였음.

## 여러 데이터셋에 걸친 그룹핑/합산 (건물 단위 점수 계산)

```python
violation_score_by_building = violations.groupby("BuildingID")["row_score"].sum()
enforcement_score = (
    aep_score.add(charges_score, fill_value=0)
             .add(litigation_score, fill_value=0)
             .add(orders_score, fill_value=0)
)
total_score = violation_score_by_building.add(enforcement_score, fill_value=0)
```

- `.groupby(key)[col].sum()` — 행 단위 점수를 건물 하나당 점수 하나로 집계.
- `.add(other, fill_value=0)` — `+`와 비슷하지만, 한쪽에 없는 건물은 `NaN`이 아니라 `0`으로 처리. 모든 건물이 모든 데이터셋에 다 등장하는 게 아니라서 필요함 (예: 위반은 있지만 AEP 기록은 없는 건물도 있음).

## 서로 다른 데이터 소스에 공통 스키마 설계하기 (`EnforcementRecord`)

- NYC Open Data의 4개 데이터셋(AEP, Charges/OMO, Litigation, Orders)은 컬럼이 거의 전부 다르지만, 개념적으로는 같은 종류의 것(=시가 이 건물에 대해 어떤 강제조치를 취했다)을 나타냄.
- 4개의 개별 TypedDict를 만드는 대신, 공통 부분집합(`source`, `date`, `description`, `is_active`, `amount`) + 소스 전용 필드(`is_landlord_fault`, Charges에서만 의미 있음)로 필드를 추렸음.
- **트레이드오프**: 공통 스키마로 통일하면 `compute_stats`가 4개 소스를 소스별 예외 처리 없이 균일하게 순회할 수 있지만, 공통 필드에 안 담기는 소스별 세부 정보는 명시적으로 되살리지 않으면 손실됨(그래서 `amount`, `is_landlord_fault`를 추가했음).
- **`is_active`가 모든 소스에 깔끔하게 안 맞았던 이유**: Charges/OMO 데이터셋의 `OMOStatusReason` 필드가 공식적으로 "이 OMO가 **종료된** 사유"라고 정의돼 있다는 걸 발견 — 즉 이 데이터셋의 모든 행은 이미 종료된 사건임. "진행 중" 상태를 나타낼 자리가 애초에 없어서 `is_active`가 항상 `False`로 무의미해짐 — 반면 Litigation은 `CaseStatus`가 실제로 `PENDING`과 `CLOSED`를 구분함. 교훈: 4개 소스 중 3개엔 의미 있는데 나머지 하나엔 "해당없음" 처리가 필요한 필드는, 사실 하나의 축이 서로 다른 두 개념(진행상태 vs 종료사유)을 동시에 떠맡고 있다는 신호임 — 그래서 `is_active`에 억지로 두 의미를 다 넣기보다 별도 필드(`is_landlord_fault`)로 분리함.

## "레코드 단위 점수 제외"와 "건물 단위 위반 0건"은 다른 개념

- `EnforcementRecord` 하나는 데이터엔 존재하지만 점수 계산에서 제외될 수 있음(예: `OMOStatusReason == "Duplicate OMO"`) — 그렇다고 그 **건물**이 위반이 없다는 뜻은 아니고, 같은 건물의 다른 레코드는 정상적으로 점수에 반영됨.
- 건물 단위에서의 결정은 다름: "API 데이터 없음"과 "진짜로 위반 0건"은 **동일하게** 취급함(둘 다 `total_score = 0`) — Phase 1 스코프에서는 그 단계까지 구분 안 하기로 함(대신 `*_fetch_success` 플래그로 별도 추적해서, 점수 계산이 아니라 explain 단계에서 단서를 달 때 씀).

## RentWise 노드 다이어그램 확장: Zillow(3개) → HPD(5개)

| 단계         | 노드                                                                                       | 새로 등장한 개념                                                                                                                                                                                                                                                                                                  |
| ------------ | ------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Zillow agent | `fetch_comps → compute_stats → explain_verdict`                                            | Lab 1 직렬 구조, API 실패 시 fallback 데이터                                                                                                                                                                                                                                                                      |
| HPD agent    | `geocode_address → fetch_violations → fetch_enforcement → compute_stats → explain_verdict` | 여전히 Lab 1 직렬 구조(그래프가 갈라지지 않음) — 다만 `fetch_enforcement` 내부에서 `asyncio.gather`로 4개 API를 동시에 호출함. 이건 **노드 하나 안에서의 Python 레벨 동시성 문제**이지, LangGraph 그래프 레벨의 병렬 브랜치 구조(Lab 2의 reducer 패턴이 필요한 것)가 아님. 그래프 자체는 여전히 하나의 직렬 체인. |

**`geocode_address`를 `fetch_violations`에 합치지 않고 별도 노드로 둔 이유**: 자유 텍스트 주소를 `bbl`로 변환하는 건 위반 기록을 조회하는 것(데이터 조회)과 근본적으로 다른 종류의 작업(지오코딩)이고, `bbl`은 HPD의 5개 데이터셋 **전부**가 필요로 하는 값이라 — 별도로 분리해두면 데이터셋마다 지오코딩을 반복 호출할 필요가 없고, 각 노드의 책임도 하나씩으로 유지됨.

---

## f-string 문법

```python
greeting = f"Hello, {name}!"
```

- `f"..."` — 문자열 안에 변수/표현식 값을 그대로 끼워 넣는 문법. `"Hello, " + name + "!"`처럼 `+`로 이어붙이는 것과 결과는 같지만 훨씬 읽기 쉬움
- `{...}` 밖의 따옴표와 안의 따옴표는 서로 다른 언어의 문법일 수 있음 — 예: `f"bbl = '{state['bbl']}'"`에서 바깥 큰따옴표는 Python 문자열 경계, `{...}` 안의 작은따옴표는 Python 딕셔너리 키 접근 문법(`state['bbl']`), `{...}` 밖의 작은따옴표는 Socrata 쿼리 문법(문자열 값을 따옴표로 감싸야 함). 세 가지 문법이 한 줄에 겹쳐 보여서 헷갈리기 쉬움 — 나눠서 읽는 습관 필요

## Socrata 쿼리 (`$where` 필터링)

- Socrata = NYC Open Data 포털(`data.cityofnewyork.us`)이 쓰는 데이터 플랫폼 회사/기술
- API 기본 호출은 전체 데이터(수백만 건)를 다 돌려주므로, SQL의 `WHERE`절과 비슷한 자체 쿼리 문법으로 필터링 필요:
  ```python
  params = {"$where": f"bbl = '{bbl}'"}
  response = requests.get(url, params=params)
  ```
- 다른 Socrata 쿼리 파라미터 예시(아직 안 씀, 참고용): `$limit`(개수 제한), `$order`(정렬), `$select`(컬럼 선택)
- Socrata API는 RentCast와 달리 `{"comparables": [...]}`처럼 감싸는 딕셔너리가 없고, **응답 자체가 곧바로 리스트**로 옴

## `TypedDict`는 런타임에 강제되지 않음

```python
class HPDAgentState(ZillowAgentState):
    bbl: str
    ...

return HPDAgentState(bbl=bbl, some_undefined_field=True)  # 에러 안 남!
```

- `TypedDict`에 정의 안 된 키를 넣어서 인스턴스를 만들어도 Python 자체는 에러를 안 냄 — 타입 체커(Pylance 등)만 경고를 띄울 뿐, 실행 시점엔 그냥 평범한 딕셔너리처럼 동작함
- **교훈**: State 필드를 빠뜨리고 코드를 짜도 조용히 실행되다가, 나중에 다른 노드가 그 필드를 찾으려 할 때(`KeyError`) 원인을 못 찾고 헤맬 수 있음 — 새 필드가 필요해지면 State 클래스 정의부터 먼저 업데이트하는 습관 필요

## Python 3.9에서 `X | None` 문법 에러

```python
is_landlord_fault: bool | None   # TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'
```

- `X | None`(Union 타입의 새 문법)은 **Python 3.10 이상 전용**. 3.9 이하에서는 이 문법 자체가 런타임 에러를 냄
- 해결: `typing.Optional` 사용
  ```python
  from typing import Optional
  is_landlord_fault: Optional[bool]
  ```
- 확인 방법: 실행 로그에 찍히는 venv 경로(`.../python3.9/site-packages/...`)로 현재 Python 버전을 알 수 있음

## `import`는 파일 전체를 실행함 — `if __name__ == "__main__":`이 필요한 이유

```python
# zillow_agent.py 맨 아래
initial_state = ZillowAgentState(...)
result = graph.invoke(initial_state)   # 이 줄도 import 시 실행되어버림!
```

```python
# hpd_agent.py
from backend.agents.zillow_agent import ZillowAgentState   # 이 한 줄이 zillow_agent.py 전체를 실행시킴
```

- Python이 `from A import B`를 실행하면, `B`만 쏙 가져오는 게 아니라 **A 파일 전체를 위에서 아래까지 한 번 실행**함 (클래스 정의, 함수 정의뿐 아니라 그 파일 맨 아래에 있던 실행 코드까지)
- 그래서 `zillow_agent.py` 맨 아래에 테스트 실행 코드가 그냥 놓여 있으면, `hpd_agent.py`가 그 파일을 import할 때마다 Zillow 파이프라인 전체가 의도치 않게 재실행됨(로그에 관계없는 RentCast 호출/에러가 섞여 나옴)
- 해결: 테스트/실행 전용 코드를 `if __name__ == "__main__":`으로 감싸기
  ```python
  if __name__ == "__main__":
      initial_state = ZillowAgentState(...)
      result = graph.invoke(initial_state)
      print(result)
  ```
- 이 블록은 "이 파일을 직접 실행했을 때만" 동작하고, 다른 파일이 import할 때는 건너뛰어짐

## `python 파일경로.py` vs `python -m 패키지.경로`

```bash
python backend/agents/hpd_agent.py     # ModuleNotFoundError: No module named 'backend'
python -m backend.agents.hpd_agent     # 정상 동작
```

- 코드 안에 `from backend.agents.zillow_agent import ...`처럼 **패키지 최상위(`backend`)부터 시작하는 import**가 있으면, Python이 그 `backend`라는 이름을 찾을 수 있는 위치에서 실행해야 함
- `python 파일경로.py`로 실행하면, Python이 모듈을 찾는 기준 위치가 **그 스크립트가 있는 폴더**가 됨 → `backend/agents/` 안에서 실행되는 셈이라 `backend`라는 폴더 자체가 안 보임
- `python -m 패키지.경로`로 실행하면, 기준 위치가 **현재 터미널이 있는 위치(보통 프로젝트 루트)**가 됨 → `backend`부터 제대로 찾아짐
- `-m` 사용 시 문법: `/` 대신 `.`으로 구분, 확장자(`.py`) 안 붙임, 반드시 프로젝트 루트에서 실행

## 동기(sync) vs 비동기(async)

- **동기**: 코드가 한 줄씩 순서대로, 앞이 끝나야 다음이 실행됨. 지금까지 쓴 `requests.get()`이 이 방식 — 응답 올 때까지 그 자리에서 완전히 멈춤
- **비동기**: 기다리는 동안(예: 네트워크 응답 대기) 다른 작업이 진행되게 양보할 수 있는 방식
- 왜 필요한가: 서로 무관한 API 호출 여러 개(AEP, Charges, Litigation, Orders)를 동기 방식으로 순서대로 부르면 소요 시간이 그대로 다 더해짐(0.5초×4=2초). 비동기로 동시에 던지면 제일 느린 것 하나 기준(약 0.5초)으로 끝남

## `httpx` — 비동기 지원 HTTP 라이브러리

`requests`는 동기 전용이라 `await`을 못 붙임. 비동기로 API를 부르려면 `httpx` 같은 라이브러리가 필요.

```python
import httpx

async def fetch_aep(bbl):
    async with httpx.AsyncClient() as client:
        params = {"$where": f"bbl = '{bbl}'"}
        response = await client.get(AEP_URL, params=params)
        response.raise_for_status()
        data = response.json()
        return data
```

| `requests` (동기)                  | `httpx` (비동기)                                             |
| ---------------------------------- | ------------------------------------------------------------ |
| `def fetch(...):`                  | `async def fetch(...):` — 함수 앞에 `async`                  |
| `requests.get(url, params=params)` | `await client.get(url, params=params)` — `client.` + `await` |
| (필요 없음)                        | `async with httpx.AsyncClient() as client:` 블록 필요        |
| `response.raise_for_status()`      | 동일                                                         |

- **`async with httpx.AsyncClient() as client:`**: `with open(file) as f:`와 같은 패턴 — 블록이 끝나면 연결을 자동으로 정리(닫음). `async`가 붙은 이유는 그 "닫는" 과정도 비동기로 처리하기 위함
- **`await client.get(...)`가 왜 필요한가**: 함수 하나만 떼어놓고 보면 "왜 기다림이 필요하지" 싶을 수 있지만, 이 함수가 `asyncio.gather`로 여러 개 동시에 묶일 때 의미가 생김 — `await`은 "서버 응답 기다리는 동안 다른 코루틴에게 실행 기회를 양보하겠다"는 신호. 이게 없으면(동기 방식이면) 한 함수가 응답 올 때까지 자리를 독점해서, 결국 순차 실행이 되어버림

## `asyncio.gather`로 부분 실패 허용하기

**기본 동작**: 여러 코루틴 중 하나라도 실패하면 즉시 예외를 던지고 나머지 결과까지 다 버려짐.

**`return_exceptions=True`를 추가하면**: 실패해도 예외를 던지지 않고, 그 자리에 예외 객체 자체를 결과로 채워서 끝까지 다 기다린 뒤 리스트로 반환.

```python
results = await asyncio.gather(
    fetch_aep(bbl),
    fetch_charges(bbl),
    fetch_litigations(bbl),
    fetch_orders(bbl),
    return_exceptions=True,
)
# 예: Orders만 실패했다면
# results = [aep결과, charges결과, litigation결과, httpx.HTTPError(...)]
```

성공/실패를 구분하려면 `isinstance()`로 각 결과가 예외 타입인지 확인:

```python
if isinstance(results[3], Exception):
    print("Orders failed")
else:
    # results[3]은 진짜 데이터
```

**HPD에서 이 방식을 택한 이유**: 4개 강제조치 소스 중 하나가 실패해도(네트워크 문제 등) 나머지 3개는 유효한 데이터이므로 살리고 싶었음 — Zillow의 "실패해도 fallback으로 계속 진행" 철학과 같은 맥락.

## 4개 소스를 공통 반복문 대신 개별 블록으로 처리하기로 한 이유

시도했던 방향(실패했던 접근):

```python
source_names = ["AEP", "Charges", "Litigation", "Order"]
for i in range(4):
    if isinstance(results[i], Exception):
        print(f"{source_names[i]} failed")
    else:
        for c in results[i]:
            record = {"source": source_names[i], "date": c[???], ...}  # 소스마다 원본 필드명이 다 다름
```

- 문제: AEP는 `AEP_START_DATE`, Charges는 `OMOCreateDate`, Litigation은 `CaseOpenDate`, Orders는 `Vacate Effective Date` — 4개 소스의 원본 필드명이 전부 다르기 때문에, 공통 반복문 하나로는 "date를 어디서 꺼낼지"조차 통일할 수 없음
- 결론: 실패 여부 체크(`isinstance`)는 4개 다 똑같은 패턴이지만, 성공했을 때의 필드 매핑(변환 로직)은 4개 소스마다 완전히 독립된 블록으로 작성하는 게 더 명확함 — 억지로 하나로 합치려다 오히려 분기 로직이 복잡해지는 경우

## `asyncio.run()`이 필요한 경우

```python
if __name__ == "__main__":
    async def test():
        result = await fetch_aep("3011787503")
        print(result)

    asyncio.run(test())
```

- `async def`로 만든 코루틴은 `await`으로만 실행할 수 있는데, 최상위 스크립트 레벨(`if __name__` 블록 등)은 `async` 함수가 아니라서 그 안에서 바로 `await`을 못 씀
- `asyncio.run(코루틴)`이 "동기 세계에서 비동기 세계로 들어가는 입구" 역할 — 이벤트 루프를 새로 만들어서 그 코루틴을 실행하고 끝나면 루프를 정리함

## [2026-09-27] fetch_enforcement 구현 중 배운 개념

### Socrata 응답은 값이 없으면 키를 아예 뺀다

```python
c["omostatusreason"]            # 키가 없으면 KeyError로 함수가 죽음
c.get("omostatusreason", "")    # 키가 없으면 기본값 "" (안전)
"actual_rescind_date" in c      # 키가 있는지 없는지 자체를 True/False로
```

- Socrata JSON은 빈 값을 `null`로 주지 않고 **키 자체를 응답에서 뺀다**. 샘플에서 확인: AEP의 `discharge_date`(Active 건), Charges의 `omostatusreason`(3건 중 2건), Orders의 `actual_rescind_date`, Litigation의 `findingofharassment`와 `penalty`
- 그래서 `fetch_violations`처럼 `c["필드"]`로만 꺼내면 소스에 따라 KeyError가 날 수 있음. 항상 있는 필드는 `c["..."]`, 없을 수 있는 필드는 `c.get(...)` 또는 `in`
- `.get("키", "")`의 두 번째 인자를 빈 문자열로 주면 뒤에 `.lower()`를 붙여도 안전함 (`None.lower()`는 에러)

**RentWise 연결**: Charges의 `amount`는 `float(c["omoawardamount"]) if "omoawardamount" in c else None`, Orders의 `is_active`는 `"actual_rescind_date" not in c`로 처리

---

### 문서(스키마)와 실제 API 값은 다르다

| 항목                     | 문서                         | 실제 API 응답                                                 |
| ------------------------ | ---------------------------- | ------------------------------------------------------------- |
| AEP `current_status`     | "Active" / "Discharged"      | `"AEP Active"` / `"AEP Discharged"`                           |
| AEP, Orders `bbl` 타입   | Number                       | 따옴표 있는 문자열 (`bbl = '...'` 쿼리가 정상 동작)           |
| Charges `omoawardamount` | Number (CSV에서는 콤마 버그) | `'556460'`, `'1455.52'` 콤마 없음 (전체 최댓값 검증은 미실시) |

- 웹페이지의 Columns 표는 필드 이름과 설명만 알려줌. **실제 값의 모양은 데이터를 찍어봐야 앎**
- CSV 다운로드와 API는 같은 데이터셋이어도 형식이 다를 수 있음. pandas 분석 때 쓴 값 비교식(`== "active"`)을 API 코드에 그대로 옮기면 안 됨
- 처음 테스트한 두 건물에서 4개 소스가 전부 `[]`였던 건 쿼리 오류가 아니라 **진짜 기록이 없어서**였음. 검증법: 각 데이터셋에서 필터 없이 샘플(`$limit`)을 뽑아 그 샘플의 bbl로 다시 호출해서, 결과가 나오면 쿼리는 정상

---

### 데이터 먼저 보기: `$limit`, `$select`, `$group`

```python
{"$limit": 3}                                                   # 필터 없이 앞의 3건
{"$select": "omostatusreason, count(*)", "$group": "omostatusreason"}   # 값별 개수 집계
```

- SQL의 `SELECT ... GROUP BY`와 같은 개념 (SoQL). 서버가 세어서 요약만 보내주므로 수십만 건을 다 받을 필요 없음
- 집계 결과에서 값이 없는 그룹은 `omostatusreason` 키 없이 `{'count': '7438'}`처럼 나옴
- "데이터가 설계보다 먼저다" 원칙의 실행 방법. 이 집계로 블랙리스트 9개가 실제로 다 존재하고, 종료 사유가 없는 건이 1.4%임을 확인함

---

### 비교식은 그 자체가 값이다 (`==`, `in`, `not in`)

```python
"is_active": c["current_status"] == "AEP Active"          # True 또는 False
"is_active": "actual_rescind_date" not in c               # True 또는 False
"is_landlord_fault": reason.lower() not in NOT_LANDLORD_FAULT_REASONS
```

- 틀린 예: `"is_active": c["current_status"]` 는 `'AEP Discharged'`라는 **문자열**이 들어감
- 파이썬은 내용이 있는 문자열을 전부 참(True)으로 취급하므로, 나중에 `if record["is_active"]:`가 Discharged도 통과시킴. TypedDict는 런타임에 타입을 검사하지 않아서 **에러 없이 점수만 조용히 틀려짐**
- 값을 복사하는 것과 조건을 평가해서 bool을 만드는 것은 다름

---

### 실패 플래그 변수 (스위치 패턴)

```python
all_ok = True
...
if isinstance(aep_result, Exception):
    print(f"AEP failed: {aep_result}")
    all_ok = False          # 4개 블록 모두 실패 분기에서 꺼짐
...
return HPDAgentState(hpd_enforcement_records=enforcement_records,
                     enforcement_fetch_success=all_ok)
```

- 하나라도 실패하면 `False`로 정함. 일부 소스가 빠진 결과로 점수를 매기면 위험도가 실제보다 낮게 나올 수 있어서, `explain_verdict`가 설명에 단서를 달게 하려는 플래그의 목적과 맞음
- 리턴할 때 State 키 이름은 정의한 이름과 **글자까지 똑같아야** 함. `hpd_enforce_records`처럼 틀리면 에러 없이 이름이 다른 키가 하나 생기고, 다음 노드는 빈 값을 봄

---

### return과 print

| 상황                                                                  | 쓰는 것  |
| --------------------------------------------------------------------- | -------- |
| 다른 코드가 값을 이어서 써야 함 (`fetch_orders`, `fetch_enforcement`) | `return` |
| 사람이 화면으로 확인만 함 (임시 `sample_test`)                        | `print`  |

- `return`은 값을 넘기면서 함수를 그 자리에서 끝냄. `for` 루프 안에 두면 첫 바퀴에서 함수가 끝남
- `asyncio.run(코루틴)`은 안의 함수 리턴값을 그대로 돌려줌: `result = asyncio.run(fetch_enforcement(state))`

---

### f-string: 표현식 전체가 중괄호 안

```python
f"Selected for AEP with {c['of_b_c_violations_at_start']} B/C violations at start"   # 정답
f"... c{['of_b_c_violations_at_start']} ..."     # 틀림: c는 글자, 대괄호는 리스트가 됨
f"... 'c.get(casetype)' ..."                     # 틀림: 중괄호가 없어서 글자 그대로 출력
```

- 바깥이 큰따옴표면 안쪽 키는 작은따옴표 (Python 3.9)
- 변수와 대괄호, 키까지 표현식 전체가 `{ }` 하나 안에 들어가야 함

---

### 디버깅 노트

| 증상                                    | 원인                                                                      | 해결                                                           |
| --------------------------------------- | ------------------------------------------------------------------------- | -------------------------------------------------------------- |
| `NameError: name 'test' is not defined` | `async def test():`는 주석 처리했는데 `asyncio.run(test())`가 살아 있었음 | 블록 전체를 같이 주석 처리                                     |
| Pylance `aep_result is not defined`     | 변수를 만드는 줄(`aep_result = results[0]`) 없이 사용                     | 변수는 값을 넣어 만든 뒤에 씀                                  |
| `KeyError: '\tomocreatedate'` (예상)    | 따옴표 안에 눈에 안 보이는 탭 문자가 들어감                               | 따옴표 안을 지우고 손으로 다시 입력. 에러 메시지의 `\t`가 단서 |
| 프롬프트가 `>>>`로 바뀜                 | 파이썬 REPL(대화형 모드)에 들어감                                         | `exit()` 또는 `Ctrl + D`                                       |
| 복붙 후 이름이 그대로 남음              | 블록을 복사한 뒤 `for c in aep_result:`, `"source"`, print 라벨을 안 바꿈 | 복사한 블록에서 소스 이름이 들어간 세 곳을 확인                |
| `results[0]`이 항상 고정                | 반복문 변수 `i`를 안 씀                                                   | 소스별 독립 블록으로 변경                                      |

- 여러 테스트 블록의 `if __name__ == "__main__":`는 전부 순서대로 실행됨. 필요 없는 블록은 `#`로 끄고(`Cmd + /`), 들여쓰기는 `Tab` / `Shift + Tab`

---

### EnforcementRecord 매핑 (4개 소스, 확정)

| 필드                | AEP                              | Charges                 | Litigation                | Order                            |
| ------------------- | -------------------------------- | ----------------------- | ------------------------- | -------------------------------- |
| `source`            | `"AEP"`                          | `"Charges"`             | `"Litigation"`            | `"Order"` (단수)                 |
| `date`              | `aep_start_date`                 | `omocreatedate`         | `caseopendate`            | `vacate_effective_date`          |
| `description`       | B/C 위반 수를 넣은 문장          | `omodescription`        | `casetype`을 넣은 문장    | 사유와 유형을 넣은 문장          |
| `is_active`         | `current_status == "AEP Active"` | 항상 `False`            | `casestatus == "PENDING"` | `"actual_rescind_date" not in c` |
| `is_landlord_fault` | `None`                           | 블랙리스트 기반         | `None`                    | `None`                           |
| `amount`            | `None`                           | `float(omoawardamount)` | `None`                    | `None`                           |

---

### is_landlord_fault: 블랙리스트 방식

```python
NOT_LANDLORD_FAULT_REASONS = ["duplicate omo", "utility account picked up by esb", "vacant land",
    "apt. vacant", "bldg. vacant", "user error", "condition not found",
    "condition does not exist", "for field visits only - cancelled"]

"is_landlord_fault": c.get("omostatusreason", "").lower() not in NOT_LANDLORD_FAULT_REASONS
```

- `omostatusreason`은 "이 OMO가 종료된 사유". 블랙리스트 9개 사유는 건물주와 무관하게 끝난 건. 나머지는 전부 `True`, 사유가 없는 건(키 없음)도 `True`
- 실측 분포(전체 514,093건): 블랙리스트 9개 약 33,100건(6.4%), 사유 없음 7,438건(1.4%), 나머지 약 92%가 `True`
- 소문자 비교(`.lower()`)를 쓰는 이유: 원본에 `'landlord Restored Service'`처럼 대소문자가 섞인 값이 있음
- **이 필드는 과실 판정이 아니라 노이즈 필터임.** 데이터셋 자체가 "건물주가 안 고쳐서 HPD가 대신 공사"한 기록이라 대부분 `True`가 정상. `True`는 "건물주 잘못이 입증됨"이 아니라 "제외 사유에 안 걸림"

---

### 알려진 한계 (인터뷰에서 "알고 있고 일정상 이렇게 했다"고 말할 수 있는 것)

1. **블랙리스트 밖의 건물주 무관 사유**: `Tenant Refused Access`(4,097), `Complainant Refused`(4,206), `Condition Different than Stated`(4,775), `Condition Previously Repaired`(34) 등 약 2.6%가 `True`로 남음. 확장하면 good/caution/danger 임계값(5, 45)을 다시 계산해야 해서 Phase 1에서는 9개 유지
2. **Orders 날짜 역전**: 발효일(2025-10-15)이 철회일(2025-01-07)보다 늦은 레코드가 있음. 날짜 비교 없이 철회일 키 유무만 봄
3. **원본 `description` 품질**: 약 150자에서 잘리고(`...10:30 am han`), `\x1a`, `ï¿½` 같은 깨진 글자가 섞임. `explain_verdict`에 넘길 때 주의
4. **Charges `is_active` 항상 False**: 종료 사유가 없는 건이 1.4% 있어서 "종료된 건만 기록"은 근사치. 55만 달러 철거 건도 사유가 없었음
5. **Litigation `PENDING` 미검증**: 샘플에서는 `CLOSED`만 확인. 진행 중 값이 실제로 `PENDING`인지는 아직 못 봄

---

### 인터뷰 대비

- **Q. 4개 소스를 왜 공통 스키마로 합쳤나?** 소스마다 필드 이름과 의미가 다르지만 "시가 이 건물에 취한 강제조치"라는 같은 개념임. 공통 모양으로 번역해 두면 `compute_stats`가 소스를 신경 쓰지 않고 리스트를 순회하며 점수만 계산함. 대신 공통 필드에 안 담기는 정보(금액, 건물주 과실 여부)는 별도 필드로 살림
- **Q. API 하나가 실패하면?** `asyncio.gather(..., return_exceptions=True)`로 나머지 결과는 살리고, `enforcement_fetch_success=False`로 표시해 `explain_verdict`가 설명에 단서를 달 수 있게 함
- **Q. 문서만 보고 짜면 안 되나?** 안 됨. 문서에는 `"Active"`인데 실제는 `"AEP Active"`였고, 값이 없으면 키가 사라지는 것도 문서에 없었음. 샘플과 집계로 실제 값을 먼저 확인함
- **Q. `is_landlord_fault`는 과실을 판정하나?** 아님. 명백히 건물주와 무관한 9개 종료 사유를 제외하는 노이즈 필터이고, 한계(위 1번)도 알고 있음
