import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path
from bot.config import (
    GMAIL_USER,
    GMAIL_APP_PASS,
    MAX_EMAILS_PER_DAY,
    MAX_EMAILS_PER_DOMAIN_PER_WEEK,
    CANDIDATE_NAME
)
from bot.db import (
    get_emails_sent_today_count,
    get_domain_emails_this_week_count,
    log_email_sent
)
from bot.hr_finder import check_mx_valid

def send_application_email(
    to_email: str,
    subject: str,
    body_text: str,
    resume_pdf_path: Path = None,
    cover_letter_pdf_path: Path = None
) -> tuple[bool, str]:
    """
    Safely sends cold outreach email via Gmail SMTP with tailored resume and cover letter PDF attachments.
    Enforces strict rate limits, domain cooldowns, and MX verification.
    """
    if not GMAIL_USER or not GMAIL_APP_PASS:
        return False, "Gmail credentials not configured."

    # 1. Validate MX records on recipient domain
    domain = to_email.split("@")[-1].lower() if "@" in to_email else ""
    if not domain or not check_mx_valid(domain):
        return False, f"Domain '{domain}' has no valid MX records (cannot receive mail)."

    # 2. Check daily email count
    sent_today = get_emails_sent_today_count()
    if sent_today >= MAX_EMAILS_PER_DAY:
        return False, f"Daily limit reached ({sent_today}/{MAX_EMAILS_PER_DAY}). Paused until tomorrow."

    # 3. Check domain weekly cooldown
    domain_sent = get_domain_emails_this_week_count(domain)
    if domain_sent >= MAX_EMAILS_PER_DOMAIN_PER_WEEK:
        return False, f"Domain cooldown active ({domain}: {domain_sent}/{MAX_EMAILS_PER_DOMAIN_PER_WEEK} this week)."

    # 4. Construct Email Message
    msg = MIMEMultipart()
    msg["From"] = f"{CANDIDATE_NAME} <{GMAIL_USER}>"
    msg["To"] = to_email
    msg["Reply-To"] = GMAIL_USER
    msg["Subject"] = subject

    msg.attach(MIMEText(body_text, "plain", "utf-8"))

    # Attachments: Resume and Cover Letter PDFs
    attachments = [resume_pdf_path, cover_letter_pdf_path]
    for att in attachments:
        if att and Path(att).exists():
            with open(att, "rb") as f:
                pdf_data = f.read()
                part = MIMEApplication(pdf_data, _subtype="pdf")
                part.add_header("Content-Disposition", "attachment", filename=Path(att).name)
                msg.attach(part)

    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20)
        server.login(GMAIL_USER, GMAIL_APP_PASS)
        server.send_message(msg)
        server.quit()
        
        log_email_sent(to_email, domain, subject, status="sent")
        return True, "Email sent successfully."
    except Exception as e:
        err_msg = str(e)
        log_email_sent(to_email, domain, subject, status=f"failed: {err_msg}")
        return False, f"SMTP Error: {err_msg}"

