from datetime import datetime, timedelta
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from sqlmodel import select
from db.session import get_session
from db.database_schema import Email, EmailDraft, Client, Campaign
import smtplib
from email.mime.text import MIMEText


class EmailSenderAgent:
    def __init__(self):
        self.session_factory = get_session
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

        while scheduled_time.weekday() in [4, 5]:  # Skip Friday(4) and Saturday(5)
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

    def send_email(self, recipient_email: str, subject: str, body: str):
        sender_email = "your-email@example.com"
        password = "your-email-password"

        msg = MIMEText(body, "html")
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = recipient_email

        with smtplib.SMTP_SSL("smtp.your-email-provider.com", 465) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, recipient_email, msg.as_string())

    def send_emails_job(self, campaign_id: int):
        with self.session_factory() as session:
            emails = session.exec(
                select(Email, EmailDraft, Client)
                .join(EmailDraft, EmailDraft.draft_id == Email.draft_id)
                .join(Client, Client.client_id == EmailDraft.client_id)
                .where(
                    EmailDraft.campaign_id == campaign_id,
                    Email.sent_at == None
                )
            ).all()

            for email, draft, client in emails:
                self.send_email(client.email, "Your Campaign Subject", email.personalized_body)
                email.sent_at = datetime.now(pytz.timezone('Asia/Dhaka'))
                session.add(email)

            session.commit()

        print(f"Emails sent successfully for campaign: {campaign_id}")
    