
# from langgraph.graph import StateGraph, START, END
# from typing import TypedDict
# from agents.draft_email_agent import DraftEmailAgent
# from agents.draft_message_agent import DraftMessageAgent

# class DState(TypedDict, total=False):
#     strategy_id: int
#     channel: str  # "email" | "whatsapp"
#     draft_id: int

# def choose_channel(st: DState):
#     return "email" if st["channel"] == "Email" else "whatsapp"

# draft_graph = StateGraph(DState)
# draft_graph.add_node("email", DraftEmailAgent())
# draft_graph.add_node("whatsapp", DraftMessageAgent())

# draft_graph.add_conditional_edges(
#     source=START,
#     path=choose_channel,
#     path_map={"email": "email", "whatsapp": "whatsapp"}
# )

# draft_graph.add_edge("email", END)
# draft_graph.add_edge("whatsapp", END)

# draft_phase = draft_graph.compile()































# from langgraph.graph import StateGraph, START, END
# from typing import TypedDict
# from agents.draft_email_agent   import DraftEmailAgent
# from agents.draft_message_agent import DraftMessageAgent
# from agents.redraft_agent       import RedraftAgent
# from agents.personaliser_agent  import PersonaliserAgent
# from agents.repersonalize_agent import RepersonalizeAgent
# # from agents.send_agent          import SendAgent       # WhatsApp / SMTP
# from db.session import get_session
# from db.database_schema import Feedback
# from langchain_core.runnables import Runnable
# import time
# from typing import Dict,Any


# _sf = get_session

# class DState(TypedDict, total=False):
#     strategy_id: int
#     channel: str                  # "email" | "whatsapp"
#     draft_id: int
#     pers_id: int
#     needs_rewrite: bool
#     needs_repersonal: bool
#     sent_id: int

# def choose_channel(st):  # ← decides first branch
#     return "email" if st["channel"] == "email" else "whatsapp"

# def wait_feedback(stage: str, flag_key: str) -> Runnable:
#     class Waiter(Runnable):
#         def _call(self, st: DState):
#             target_id = st["draft_id"] if stage == "draft" else st["pers_id"]
#             while True:
#                 with _sf() as s:
#                     fb = (
#                         s.query(Feedback)
#                           .filter_by(email_id=target_id, stage=stage)
#                           .order_by(Feedback.created_at.desc())
#                           .first()
#                     )
#                     if fb:
#                         return {
#                             flag_key: fb.wants_change,  # ← boolean: wants rewrite?
#                             "fb_comments": fb.comments
#                         }
#                 time.sleep(3)

#         def invoke(self, input: DState, config=None) -> Dict[str, Any]:  # ⬅️ mandatory now
#             return self._call(input)

#     return Waiter()



# def redraft_needed(st):       # conditional edge
#     return "redo" if st.get("needs_rewrite") else "next"

# def repers_needed(st):
#     return "redo" if st.get("needs_repersonal") else "send"

# g = StateGraph(DState)

# g.add_node("email",    DraftEmailAgent())
# g.add_node("whatsapp", DraftMessageAgent())
# g.add_node("wait_draft_fb",  wait_feedback("draft", "needs_rewrite"))
# g.add_node("redraft",        RedraftAgent())
# g.add_node("personalise",    PersonaliserAgent())
# g.add_node("wait_pers_fb",   wait_feedback("personalised", "needs_repersonal"))
# g.add_node("repersonalise",  RepersonalizeAgent())
# # g.add_node("send", SendAgent())

# # ENTRY CORRECTION
# g.add_conditional_edges(
#     source=START,
#     path=choose_channel,
#     path_map={"email": "email", "whatsapp": "whatsapp"}
# )

# g.add_edge("email",    "wait_draft_fb")
# g.add_edge("whatsapp", "wait_draft_fb")

# # loop draft
# g.add_conditional_edges(
#     source="wait_draft_fb",
#     path=redraft_needed,        # <== function returning "redo" or "next"
#     path_map={"redo": "redraft", "next": "personalise"}
# )

# g.add_edge("redraft", "wait_draft_fb")

# # # personalise loop
# # g.add_edge("personalise", "wait_pers_fb")
# # g.add_conditional_edges(
# #     source="wait_pers_fb",
# #     path=repers_needed,  # function first
# #     path_map={"redo": "repersonalise", "send": "send"}
# # )

# # g.add_edge("repersonalise", "wait_pers_fb")

# # g.add_edge("send", END)

# g.add_edge("personalise", END)

# draft_graph = g.compile()



