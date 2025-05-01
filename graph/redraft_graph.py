from langgraph.graph import StateGraph, START, END
from typing import TypedDict
from agents.redraft_agent import RedraftAgent

class RState(TypedDict, total=False):
    draft_id: int
    needs_rewrite: bool
    fb_comments: str
    channel: str
    draft_content: str       
    pers_id: int             
    status: str              

def redraft_needed(st: RState):
    return "redo" if st.get("needs_rewrite") else "end"

redraft_graph = StateGraph(RState)


redraft_graph.add_node("redraft", RedraftAgent())


redraft_graph.add_conditional_edges(
    source=START,
    path=redraft_needed,
    path_map={"redo": "redraft", "end": END}
)


redraft_graph.add_edge("redraft", END)

redraft_phase = redraft_graph.compile()
