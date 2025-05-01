from langgraph.graph import StateGraph, START, END
from typing import TypedDict
from agents.strategy_agent import StrategyAgent
from db.session import get_session
from db.database_schema import Profile, Communication

_sf = get_session


class SState(TypedDict, total=False):
    client_id: int
    campaign_id: int        
    preq_ok: bool
    strategy_id: int



def check(st: SState) -> SState:
    cid = st["client_id"]
    with _sf() as s:
        prof = s.query(Profile).filter_by(client_id=cid).first()
        comm = s.query(Communication).filter_by(client_id=cid).count()

        profile_ok = bool(prof and prof.summary and prof.interests)
        
        st["preq_ok"] = bool(profile_ok and comm)
    return st

def need_build(st: SState) -> str:
    return "build" if st["preq_ok"] else "skip"

def skip_node(state: SState) -> SState:
    return state


g = StateGraph(SState)

g.add_node("check", check)
g.add_node("build", StrategyAgent())
g.add_node("skip", skip_node)

g.add_edge(START, "check")

g.add_conditional_edges(
    source="check",
    path=need_build,
    path_map={"build": "build", "skip": "skip"}
)

g.add_edge("build", END)
g.add_edge("skip", END)

strategy_graph = g.compile()
