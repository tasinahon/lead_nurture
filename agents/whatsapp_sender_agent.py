# from __future__ import annotations
# from datetime import datetime, timedelta
# import asyncio, os, json, sys, pytz
# from apscheduler.schedulers.asyncio import AsyncIOScheduler
# from sqlmodel import select
# from db.session import SessionLocal
# from db.database_schema import Message, MessageDraft, Client
# from langchain_mcp_adapters.client import MultiServerMCPClient
# from langgraph.prebuilt import create_react_agent
# from langchain_google_genai import ChatGoogleGenerativeAI
# from dotenv import load_dotenv
# import logging
# from typing import Any
# import ast
# # from langchain_mcp_adapters.tools import show_tools


# load_dotenv()

# # Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger("WhatsAppSender")

# # ── constants ────────────────────────────────────────────────
# TZ = pytz.timezone("Asia/Dhaka")
# MCP_WHATSAPP_CFG = {
#     "whatsapp": {
#         "command": os.getenv("UV_EXE", r"C:\Users\Lenovo\.local\bin\uv.exe"),
#         "args": [
#             "--directory",
#             os.getenv("MCP_DIR", r"E:\whatsappmcp\whatsapp-mcp\whatsapp-mcp-server"),
#             "run",
#             "main.py",
#         ],
#         "transport": "stdio",
#     }
# }
# WHATSAPP_HOURS = (9, 23)
# WEEKEND_DAYS = {4, 5}  # Friday and Saturday


# class WhatsAppSenderAgent:
#     def __init__(self) -> None:
#         self.session_factory = SessionLocal
#         self.scheduler = AsyncIOScheduler(timezone="Asia/Dhaka")
#         self.scheduler.start()
        
#     def all_messages_approved(self, campaign_id: int) -> bool:
#         """Check if all messages in a campaign are approved"""
#         with self.session_factory() as s:
#             msgs = s.exec(
#                 select(Message).join(MessageDraft).where(
#                     MessageDraft.campaign_id == campaign_id
#                 )
#             ).all()
#             return all(m.approved_at for m in msgs)

#     @staticmethod
#     def _next_office_slot() -> datetime:
#         """Calculate the next valid time slot for sending messages"""
#         now = datetime.now(TZ)
#         start, end = WHATSAPP_HOURS
        
#         # If within business hours, send in 1 minute
#         if start <= now.hour < end:
#             return now + timedelta(minutes=1)
        
#         # Calculate next valid day
#         days_to_add = 1
#         while True:
#             next_day = now + timedelta(days=days_to_add)
#             # Skip weekends
#             if next_day.weekday() not in WEEKEND_DAYS:
#                 return next_day.replace(
#                     hour=start, minute=0, second=0, microsecond=0
#                 )
#             days_to_add += 1

#     def schedule_messages(self, campaign_id: int) -> None:
#         """Schedule messages for a campaign"""
#         if not self.all_messages_approved(campaign_id):
#             logger.warning(f"Not all messages approved for campaign {campaign_id}")
#             return

#         run_at = self._next_office_slot()
#         with self.session_factory() as s:
#             msgs = s.exec(
#                 select(Message).join(MessageDraft).where(
#                     MessageDraft.campaign_id == campaign_id
#                 )
#             ).all()
#             for m in msgs:
#                 m.scheduled_at = run_at
#                 s.add(m)
#             s.commit()

#         self.scheduler.add_job(
#             self._send_job,
#             "date",
#             run_date=run_at,
#             args=[campaign_id],
#         )
#         logger.info(f"Campaign {campaign_id} scheduled for {run_at}")

#     async def send_messages_now(self, campaign_id: int) -> None:
#         """Send all approved messages for a campaign immediately."""
#         await self._send_job(campaign_id)

#     async def _send_job(self, campaign_id: int) -> None:
#         """Core send logic, with batching and full exception trace on failure."""
#         client = None
#         try:
#             logger.info(f"Starting send job for campaign {campaign_id}")

#             client = MultiServerMCPClient(MCP_WHATSAPP_CFG)
#             tools = await client.get_tools()
#             logger.info(f"Loaded {len(tools)} tools")

#             llm = ChatGoogleGenerativeAI(
#                 model="gemini-1.5-flash",
#                 temperature=0.0,
#                 max_retries=3
#             )
#             agent = create_react_agent(llm, tools)

#             with self.session_factory() as s:
#                 stmt = (
#                     select(Message, MessageDraft, Client)
#                      .join(MessageDraft, Message.draft_id == MessageDraft.draft_id)
#                      .join(Client, Client.client_id == MessageDraft.contact_id)
#                      .where(
#                          MessageDraft.campaign_id == campaign_id,
#                          MessageDraft.day == 1,
#                          Message.sent_at.is_(None)
#                      )
#                 )
#                 rows = s.exec(stmt).all()

#             if not rows:
#                 logger.info(f"No messages to send for campaign {campaign_id}")
#                 return

#             logger.info(f"Processing {len(rows)} messages")

#             send_tasks = []
#             for msg, draft, cli in rows:
#                 number = cli.whatsapp
#                 text = msg.personalized_text or draft.message_text
#                 send_tasks.append(self._send_whatsapp(agent, number, text, msg))

#             batch_size = 5
#             for i in range(0, len(send_tasks), batch_size):
#                 await asyncio.gather(*send_tasks[i : i + batch_size])
#                 await asyncio.sleep(1)

#             logger.info(f"Campaign {campaign_id} messages processed")

#         except Exception:
#             logger.exception(f"Error in send job for campaign {campaign_id}")
#         finally:
#             with self.session_factory() as s:
#                 s.commit()


#     async def _send_whatsapp(
#         self,
#         agent: Any,
#         number: str,
#         text: str,
#         msg: Message
#     ) -> bool:
#         """Send a WhatsApp message, inspecting tool output & handling both JSON & Python repr."""
#         try:
#             logger.info(f"Sending to {number}")

#             # 1) search_contacts
#             search_cmd = f'search_contacts "{number}"'
#             search_run = await agent.ainvoke({
#                 "messages": [{"role": "user", "content": search_cmd}]
#             })
#             # show_tools(search_run)

#             raw = search_run["messages"][-1].content
#             logger.debug(f"Raw search_contacts output: {raw!r}")

#             # 2) try JSON first, then Python literal
#             contacts = []
#             try:
#                 contacts = json.loads(raw)
#             except json.JSONDecodeError:
#                 try:
#                     contacts = ast.literal_eval(raw)
#                 except Exception as e:
#                     logger.warning(f"Could not parse contacts: {e}; raw was: {raw!r}")

#             # 3) pick a JID
#             if contacts and isinstance(contacts, list) and "jid" in contacts[0]:
#                 jid = contacts[0]["jid"]
#                 logger.info(f"✅ Found contact: {contacts[0].get('name','<no-name>')} → {jid}")
#             else:

#                 normalized = number.lstrip("+")
#                 # if no country code, add Bangladesh code
#                 if not normalized.startswith("880"):
#                     normalized = "880" + normalized.lstrip("0")
#                 jid = f"{normalized}@s.whatsapp.net"
#                 # ensure E.164 format (adjust prefix logic as needed)
#                 # if not number.startswith("+"):
#                 #     number = "+880" + number.lstrip("0")
#                 # jid = f"{number}@s.whatsapp.net"
#                 logger.warning(f"⚠️  Falling back to direct JID: {jid}")

#             # 4) send_message
#             send_cmd = f'send_message "{jid}" "{text}"'
#             send_run = await agent.ainvoke({
#                 "messages": [{"role": "user", "content": send_cmd}]
#             })
#             # show_tools(send_run)

#             # 5) mark as sent
#             with self.session_factory() as s:
#                 msg.sent_at = datetime.now(TZ)
#                 s.add(msg)
#                 s.commit()

#             logger.info(f"Message sent to {jid}")
#             return True

#         except Exception:
#             logger.exception(f"Error sending to {number}")
#             with self.session_factory() as s:
#                 msg.error = str(sys.exc_info()[1])
#                 s.add(msg)
#                 s.commit()
#             return False








# # whatsapp_sender_agent.py
# from __future__ import annotations
# from datetime import datetime, timedelta
# import asyncio, os, json, sys, pytz
# from apscheduler.schedulers.asyncio import AsyncIOScheduler
# from sqlmodel import select
# from db.session import SessionLocal
# from db.database_schema import Message, MessageDraft, Client
# from langchain_mcp_adapters.client import MultiServerMCPClient
# from langgraph.prebuilt import create_react_agent
# from langchain_google_genai import ChatGoogleGenerativeAI
# from dotenv import load_dotenv

# load_dotenv()

# # ── constants ────────────────────────────────────────────────
# TZ = pytz.timezone("Asia/Dhaka")
# MCP_WHATSAPP_CFG = {
#     "whatsapp": {
#         "command": os.getenv("UV_EXE", r"C:\Users\Lenovo\.local\bin\uv.exe"),
#         "args": [
#             "--directory",
#             os.getenv("MCP_DIR", r"E:\campaign_ai\whatsapp-mcp\whatsapp-mcp-server"),
#             "run",
#             "main.py",
#         ],
#         "transport": "stdio",
#     }
# }
# WHATSAPP_HOURS = (9, 23)
# WEEKEND_DAYS = {4, 5}


# class WhatsAppSenderAgent:
#     def __init__(self) -> None:
#         self.session_factory = SessionLocal
#         self.scheduler = AsyncIOScheduler(timezone="Asia/Dhaka")
#         self.scheduler.start()

#     def all_messages_approved(self, campaign_id: int) -> bool:
#         with self.session_factory() as s:
#             msgs = s.exec(
#                 select(Message).join(MessageDraft).where(
#                     MessageDraft.campaign_id == campaign_id
#                 )
#             ).all()
#             return all(m.approved_at for m in msgs)

#     @staticmethod
#     def _next_office_slot() -> datetime:
#         now = datetime.now(TZ)
#         start, end = WHATSAPP_HOURS
#         if start <= now.hour < end:
#             return now + timedelta(minutes=1)

#         nxt = (now + timedelta(days=1)).replace(hour=start, minute=0,
#                                                second=0, microsecond=0)
#         while nxt.weekday() in WEEKEND_DAYS:
#             nxt += timedelta(days=1)
#         return nxt

#     def schedule_messages(self, campaign_id: int) -> None:
#         if not self.all_messages_approved(campaign_id):
#             print(f"[WA] Not all messages approved for campaign {campaign_id}")
#             return

#         run_at = self._next_office_slot()
#         with self.session_factory() as s:
#             msgs = s.exec(
#                 select(Message).join(MessageDraft).where(
#                     MessageDraft.campaign_id == campaign_id
#                 )
#             ).all()
#             for m in msgs:
#                 m.scheduled_at = run_at
#                 s.add(m)
#             s.commit()

#         self.scheduler.add_job(
#             self._send_job,
#             "date",
#             run_date=run_at,
#             args=[campaign_id],
#         )
#         print(f"[WA] Campaign {campaign_id} scheduled {run_at}")

#     async def send_messages_now(self, campaign_id: int) -> None:
#         await self._send_job(campaign_id)

#     async def _send_job(self, campaign_id: int) -> None:
#         llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.0)
#         client = MultiServerMCPClient(MCP_WHATSAPP_CFG)
#         tools = await client.get_tools()
#         agent = create_react_agent(llm, tools)

#         with self.session_factory() as s:
#             rows = s.exec(
#                 select(Message, MessageDraft, Client)
#                 .join(MessageDraft, Message.draft_id == MessageDraft.draft_id)
#                 .join(Client, Client.client_id == MessageDraft.contact_id)
#                 .where(MessageDraft.campaign_id == campaign_id,
#                        MessageDraft.day == 1)
#             ).all()

#             for msg, draft, cli in rows:
#                 number = cli.whatsapp
#                 text = msg.personalized_text or draft.message_text
#                 ok = await self._send_whatsapp(agent, number, text)
#                 if ok:
#                     msg.sent_at = datetime.now(TZ)
#                     s.add(msg)

#             s.commit()
#         print(f"[WA] Campaign {campaign_id} messages sent")

#     async def _send_whatsapp(self, agent, number_or_name: str, text: str) -> bool:
#         try:
#             search_cmd = f'search_contacts "{number_or_name}"'
#             search = await agent.ainvoke({"messages": [{"role": "user", "content": search_cmd}]})
#             contacts = json.loads(search["messages"][-1].content)
#             jid = contacts[0]["jid"] if contacts else f"{number_or_name}@s.whatsapp.net"

#             send_cmd = f'send_message "{jid}" "{text}"'
#             await agent.ainvoke({"messages": [{"role": "user", "content": send_cmd}]})
#             print(f"[WA] SENT → {jid}")
#             return True
#         except Exception as e:
#             print(f"[WA] ERROR to {number_or_name}: {e}")
#             return False





# # whatsapp_sender_agent.py
# from datetime import datetime, timedelta
# import asyncio, os, json, pytz
# from apscheduler.schedulers.background import BackgroundScheduler
# from sqlmodel import select
# from db.session import SessionLocal
# from db.database_schema import Message, MessageDraft, Client
# from langchain_mcp_adapters.client import MultiServerMCPClient
# from langgraph.prebuilt import create_react_agent
# from langchain_google_genai import ChatGoogleGenerativeAI      # <– light-weight, low-temp
# from dotenv import load_dotenv

# load_dotenv()

# # ── constants ────────────────────────────────────────────────
# TZ = pytz.timezone("Asia/Dhaka")
# MCP_WHATSAPP_CFG = {                      # spawn your MCP server exactly once
#     "whatsapp": {
#         "command": os.getenv("UV_EXE", r"C:\Users\Lenovo\.local\bin\uv.exe"),
#         "args": [
#             "--directory",
#             os.getenv("MCP_DIR", r"E:\campaign_ai\whatsapp-mcp\whatsapp-mcp-server"),
#             "run",
#             "main.py",
#         ],
#         "transport": "stdio",
#     }
# }
# WHATSAPP_HOURS = (9, 22)                 # inclusive start, exclusive end
# WEEKEND_DAYS   = {4, 5}                  # Fri (4) & Sat (5)

# class WhatsAppSenderAgent:
#     """
#     • Waits until ALL Message rows for a campaign are approved
#     • Schedules them for the next <office-hour> slot (9 AM – 10 PM, Sun-Thu)
#     • Uses whatsapp-mcp's `search_contacts` + `send_message` tools
#     """

#     def __init__(self) -> None:
#         self.session_factory = SessionLocal
#         self.scheduler       = BackgroundScheduler(timezone="Asia/Dhaka")
#         self.scheduler.start()

#     # ── helpers ────────────────────────────────────────────
#     def all_messages_approved(self, campaign_id: int) -> bool:
#         with self.session_factory() as s:
#             msgs = s.exec(
#                 select(Message).join(MessageDraft).where(
#                     MessageDraft.campaign_id == campaign_id
#                 )
#             ).all()
#             return all(m.approved_at for m in msgs)

#     @staticmethod
#     def _next_office_slot() -> datetime:
#         """Return the next time inside 09:00-22:00 *Sunday-Thursday*."""
#         now = datetime.now(TZ)

#         start, end = WHATSAPP_HOURS
#         # and now.weekday() not in WEEKEND_DAYS
#         if start <= now.hour < end :
#             return now + timedelta(minutes=1)

#         # Set to next day 09:00
#         nxt = (now + timedelta(days=1)).replace(hour=start, minute=0,
#                                                second=0, microsecond=0)
#         # Skip weekends
#         while nxt.weekday() in WEEKEND_DAYS:
#             nxt += timedelta(days=1)
#         return nxt

#     # ── public scheduling API ─────────────────────────────
#     def schedule_messages(self, campaign_id: int) -> None:
#         if not self.all_messages_approved(campaign_id):
#             print(f"[WA] Not all messages approved for campaign {campaign_id}")
#             return

#         run_at = self._next_office_slot()
#         with self.session_factory() as s:
#             msgs = s.exec(
#                 select(Message).join(MessageDraft).where(
#                     MessageDraft.campaign_id == campaign_id
#                 )
#             ).all()
#             for m in msgs:
#                 m.scheduled_at = run_at
#                 s.add(m)
#             s.commit()

#         # wrap async job for APScheduler
#         self.scheduler.add_job(
#             lambda cid=campaign_id: asyncio.run(self._send_job(cid)),
#             "date",
#             run_date=run_at,
#         )
#         print(f"[WA] Campaign {campaign_id} scheduled {run_at}")

#     # ── core send logic (async) ────────────────────────────
#     async def _send_job(self, campaign_id: int) -> None:
#         llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.0)
#         client = MultiServerMCPClient(MCP_WHATSAPP_CFG)
#         tools  = await client.get_tools()                        # e.g. send_message, search_contacts
#         agent  = create_react_agent(llm, tools)

#         with self.session_factory() as s:
#             rows = s.exec(
#                 select(Message, MessageDraft, Client)
#                 .join(MessageDraft, Message.draft_id == MessageDraft.draft_id)
#                 .join(Client, Client.client_id == MessageDraft.contact_id)
#                 .where(MessageDraft.campaign_id == campaign_id,
#                        MessageDraft.day == 1)                    # adjust if multi-day
#             ).all()

#             for msg, draft, cli in rows:
#                 number = cli.whatsapp     # pick your field
#                 text   = msg.personalized_text or draft.message_text

#                 ok = await self._send_whatsapp(agent, number, text)
#                 if ok:
#                     msg.sent_at = datetime.now(TZ)
#                     s.add(msg)

#             s.commit()
#         print(f"[WA] Campaign {campaign_id} messages sent")

#     # ── per-message helper ────────────────────────────────
#     async def _send_whatsapp(self, agent, number_or_name: str, text: str) -> bool:
#         """
#         1. search_contacts to resolve a JID
#         2. send_message to that JID
#         Returns True on success, False otherwise.
#         """
#         try:
#             # 1. try name/number search
#             search = await agent.ainvoke({"messages":[{"role":"user",
#                           "content": f'search_contacts "{number_or_name}"'}]})
#             contacts = json.loads(search["messages"][-1].content)
#             jid = contacts[0]["jid"] if contacts else f"{number_or_name}@s.whatsapp.net"

#             # 2. send the message
#             cmd = f'send_message "{jid}" "{text}"'
#             await agent.ainvoke({"messages":[{"role":"user","content": cmd}]})
#             print(f"[WA] SENT → {jid}")
#             return True
#         except Exception as e:
#             print(f"[WA] ERROR to {number_or_name}: {e}")
#             return False
