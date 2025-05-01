from agents.profile_builder_agent import ProfileBuilderAgent
from agents.strategy_agent import StrategyAgent
from langgraph.graph import StateGraph,END,START
from typing import TypedDict
from agents.scraper_agent import ScraperAgent
from typing_extensions import Annotated

class ClientState(TypedDict):
    client_id: Annotated[int, "skip"]

g = StateGraph(state_schema=ClientState)

g.set_entry_point("scrape")


g.add_node("scrape", ScraperAgent())
g.add_node("profile", ProfileBuilderAgent())


g.add_edge("scrape", "profile")
g.add_edge("profile", END)


flow = g.compile()


flow = g.compile()
