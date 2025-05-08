# from sqlmodel import Session, select
# from db.database_schema import EmailDraft  # Adjust import based on your structure
# from db.session import get_session

# def fix_email_draft_days():
#     with get_session() as session:
#         drafts = session.exec(select(EmailDraft)).all()

#         for draft in drafts:
#             if isinstance(draft.day, str) and draft.day.lower().startswith("day"):
#                 try:
#                     day_num = int(draft.day.strip().split()[-1])
#                     draft.day = day_num
#                     session.add(draft)
#                     print(f"Updated draft_id={draft.draft_id} to day={day_num}")
#                 except Exception as e:
#                     print(f"Skipping draft_id={draft.draft_id} due to error: {e}")

#         session.commit()
#         print("Day fields fixed.")

# # Run it
# fix_email_draft_days()
