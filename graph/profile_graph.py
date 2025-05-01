from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated, Hashable, Any
from agents.profile_builder_agent import ProfileBuilderAgent
from db.session import get_session
from db.database_schema import ScrapedData, ContextQuestion, Profile



_sf = get_session

class PState(TypedDict, total=False):
    client_id: int
    scraped_ok: bool
    cq_ok: bool
    profile_id: int
    status: str


def check_ready(st: PState) -> PState:
    cid = st["client_id"]
    with _sf() as s:
        st["scraped_ok"] = bool(s.query(ScrapedData).filter_by(client_id=cid).count())
        st["cq_ok"]      = bool(s.query(ContextQuestion).filter_by(client_id=cid).count())
    return st

def need_build(st: PState) -> str:          
    return "build" if st["scraped_ok"] else "end"


g = StateGraph(PState)

g.add_node("check", check_ready)
g.add_node("build", ProfileBuilderAgent())


g.add_edge(START, "check")


g.add_conditional_edges(
    source="check",
    path=need_build,                       
    path_map={"build": "build", "end": END}
)

g.add_edge("build", END)

profile_graph = g.compile()
