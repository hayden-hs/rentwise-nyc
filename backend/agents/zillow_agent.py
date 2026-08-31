from langchain_openai import ChatOpenAI
from typing import TypedDict, Literal
from langgraph.graph import END, START, StateGraph
# from IPython.display import Image, display
from dotenv import load_dotenv



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

load_dotenv()

llm = ChatOpenAI(model="gpt-5-mini")

def fetch_comps(state: ZillowAgentState) -> ZillowAgentState:
    print(f"Received input: {state['address']}, {state['user_rent']}, {state['bedrooms']}")

    dummy_comp = {
        "address": "776, Franklin Ave, Brooklyn, NY, 11238",
        "rent": 4150,
        "bedrooms": 2,
    }

    return ZillowAgentState(comps=[dummy_comp])

def compute_stats(state:ZillowAgentState) -> ZillowAgentState:
    rent_list = [comp["rent"] for comp in state["comps"]]
    avg_comp_rent = sum(rent_list) / len(rent_list) 

    user_rent = state["user_rent"]

    diff_pct = (user_rent - avg_comp_rent) / avg_comp_rent * 100 # user_rent?이건 어디서 가져와야되는지모르겠음

    if diff_pct > 10:
        verdict_label = "overpriced"
    elif diff_pct < -10:
        verdict_label = "underpriced"
    else: 
        verdict_label = "fair"

    return ZillowAgentState(
        avg_comp_rent = avg_comp_rent, 
        diff_pct = diff_pct, 
        verdict_label = verdict_label)

def explain_verdict(state: ZillowAgentState) -> ZillowAgentState:
    structured_llm = llm.with_structured_output(VerdictExplanation)

    explanation_prompt = f"""
    Write an explanation for this rent fairness verdict:
    Verdict: {state['verdict_label']} 
    Difference from average: {state['diff_pct']}% 
    Average comp rent: ${state['avg_comp_rent']} 
    User's rent: ${state['user_rent']}
    Provide a price_explanation and a negotiation_comment.
    """

    explanation_result = structured_llm.invoke(explanation_prompt)

    return ZillowAgentState(price_explanation = explanation_result["price_explanation"], negotiation_comment = explanation_result["negotiation_comment"])

builder = StateGraph(ZillowAgentState)
builder.add_node("fetch_comps", fetch_comps)
builder.add_node("compute_stats", compute_stats)
builder.add_node("explain_verdict", explain_verdict)
builder.add_edge(START, "fetch_comps")
builder.add_edge("fetch_comps", "compute_stats")
builder.add_edge("compute_stats", "explain_verdict")
builder.add_edge("explain_verdict", END)
graph = builder.compile()

# display(Image(graph.get_graph().draw_mermaid_png()))

initial_state = ZillowAgentState(
    address="776 Franklin Ave, Brooklyn, NY, 11238",
    user_rent=4150,
    bedrooms=2,
)
result = graph.invoke(initial_state)
print(result)