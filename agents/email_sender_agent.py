from datetime import datetime, timedelta
import pytz
import os
from apscheduler.schedulers.background import BackgroundScheduler
from sqlmodel import select
from db.session import get_session
from db.database_schema import Email, EmailDraft, Client
import smtplib
from email.mime.text import MIMEText
from db.session import SessionLocal
from email.message import EmailMessage
import email.utils
import ssl



class EmailSenderAgent:
    def __init__(self):
        self.session_factory = SessionLocal
        self.scheduler = BackgroundScheduler(timezone="Asia/Dhaka")
        self.scheduler.start()

    def all_emails_approved(self, campaign_id: int) -> bool:
        with self.session_factory() as session:
            emails = session.exec(
                select(Email).join(EmailDraft).where(
                    EmailDraft.campaign_id == campaign_id
                )
            ).all()
            return all(email.approved_at is not None for email in emails)

    def get_next_office_hour(self) -> datetime:
        tz = pytz.timezone('Asia/Dhaka')
        now = datetime.now(tz)
        scheduled_time = now.replace(hour=9, minute=0, second=0, microsecond=0)

        if now.hour >= 18:
            scheduled_time += timedelta(days=1)

        while scheduled_time.weekday() in [4, 5]: 
            scheduled_time += timedelta(days=1)

        return scheduled_time
    
    def get_next_office_hour(self) -> datetime:
        tz = pytz.timezone('Asia/Dhaka')
        now = datetime.now(tz)

    
        if 9 <= now.hour < 18 and now.weekday() < 4:  # Weekday 0–3 → Mon–Thu
            return now + timedelta(minutes=1)  
        else:
            # Next weekday at 9 AM
            scheduled_time = now.replace(hour=9, minute=0, second=0, microsecond=0)

            # Move to next day if current time is past 6PM or it's a holiday (Fri/Sat)
            if now.hour >= 18 or now.weekday() >= 4:
                scheduled_time += timedelta(days=1)

            # Skip weekends: Fri (4) and Sat (5)
            while scheduled_time.weekday() in [4, 5]:
                scheduled_time += timedelta(days=1)

        return scheduled_time


    def schedule_emails(self, campaign_id: int):
        if not self.all_emails_approved(campaign_id):
            print(f"Not all emails approved for campaign: {campaign_id}")
            return

        scheduled_time = self.get_next_office_hour()

        with self.session_factory() as session:
            emails = session.exec(
                select(Email).join(EmailDraft).where(
                    EmailDraft.campaign_id == campaign_id
                )
            ).all()

            for email in emails:
                email.scheduled_at = scheduled_time
                session.add(email)

            session.commit()

        self.scheduler.add_job(
            self.send_emails_job,
            'date',
            run_date=scheduled_time,
            args=[campaign_id]
        )

        print(f"Emails scheduled for campaign {campaign_id} at {scheduled_time}")

    # dummy
    

    # def schedule_emails(self, campaign_id: int):
    #     if not self.all_emails_approved(campaign_id):
    #         print(f"Not all emails approved for campaign: {campaign_id}")
    #         return

    #     # ⚠️ Schedule 1 minute from now
    #     scheduled_time = datetime.now() + timedelta(minutes=1)

    #     with self.session_factory() as session:
    #         emails = session.exec(
    #             select(Email).join(EmailDraft).where(
    #                 EmailDraft.campaign_id == campaign_id
    #             )
    #         ).all()

    #         for email in emails:
    #             email.scheduled_at = scheduled_time
    #             session.add(email)

    #         session.commit()

    #     self.scheduler.add_job(
    #         self.send_emails_job,
    #         'date',
    #         run_date=scheduled_time,
    #         args=[campaign_id]
    #     )

    #     print(f"[TEST MODE] Emails scheduled for campaign {campaign_id} at {scheduled_time}")




    
    def send_email(self, recipient_email: str, subject: str, body: str):
        host     = os.getenv("SMTP_HOST", "mail.privateemail.com")
        port     = int(os.getenv("SMTP_PORT", "587"))
        username = os.getenv("SMTP_EMAIL")
        password = os.getenv("SMTP_PASSWORD")
        
        print(recipient_email)

        
        msg = EmailMessage()
        msg["From"] = email.utils.formataddr(("FabricX AI", username))
        msg["To"] = recipient_email
        msg["Subject"] = subject
        
        msg.set_content("This email requires an HTML‑capable client.")
        
        msg.add_alternative(body, subtype="html")

        
        context = ssl.create_default_context()

        try:
            with smtplib.SMTP(host, port, local_hostname="fabricxai.com") as smtp:
                smtp.starttls(context=context)          
                smtp.login(username, password)
                smtp.send_message(msg)
            print(f"[SENT] Email to {recipient_email}")
        except Exception as e:
            print(f"[ERROR] Failed to send email to {recipient_email}: {e}")
    

    def send_emails_job(self, campaign_id: int):
        
        with self.session_factory() as session:
           
            drafts = session.exec(
                select(EmailDraft).where(EmailDraft.campaign_id == campaign_id, EmailDraft.day == 1)
            ).all()
            print("Drafts Found:", len(drafts))

            
            emails = session.exec(
                select(Email).where(Email.draft_id.in_([d.draft_id for d in drafts]))
            ).all()
            print("Emails Found:", len(emails))

            # Step 3: Check Clients exist for those contact_ids
            client_ids = [d.contact_id for d in drafts]
            clients = session.exec(select(Client).where(Client.client_id.in_(client_ids))).all()
            print("Clients Found:", len(clients))

            results = session.exec(
                select(Email, EmailDraft, Client)
                .join(EmailDraft, Email.draft_id == EmailDraft.draft_id)
                .join(Client, Client.client_id == EmailDraft.contact_id)
                .where(
                    EmailDraft.campaign_id == campaign_id,
                    EmailDraft.day == 1,
                    # Email.sent_at == None
                )
            ).all()
            print(results)

            for email, draft, client in results:
                print("body----------------------")
                print(email)
                self.send_email(client.email, draft.subject, email.personalized_body)
                email.sent_at = datetime.now(pytz.timezone('Asia/Dhaka'))
                session.add(email)

            session.commit()

        print(f"Emails sent successfully for campaign: {campaign_id}")
