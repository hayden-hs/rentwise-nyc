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
