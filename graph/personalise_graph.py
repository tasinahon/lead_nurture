from langgraph.graph import StateGraph, START, END
from typing import TypedDict
from agents.email_personaliser_agent import EmailPersonaliserAgent
from agents.message_personaliser_agent import MessagePersonaliserAgent

class PState(TypedDict, total=False):
    pers_id: int
    channel: str
    needs_repersonal: bool
    sent_id: int

def choose_personaliser(st: PState):
    return "email_personalise" if st.get("channel") == "email" else "message_personalise"

personalise_graph = StateGraph(PState)

personalise_graph.add_node("email_personalise", EmailPersonaliserAgent())
personalise_graph.add_node("message_personalise", MessagePersonaliserAgent())

personalise_graph.add_conditional_edges(
    source=START,
    path=choose_personaliser,
    path_map={
        "email_personalise": "email_personalise",
        "message_personalise": "message_personalise"
    }
)

personalise_graph.add_edge("email_personalise", END)
personalise_graph.add_edge("message_personalise", END)

personalise_phase = personalise_graph.compile()
