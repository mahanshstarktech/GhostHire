import urllib.request
import urllib.parse
import json
import html
from pathlib import Path
from bot.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

def send_message(text: str, parse_mode: str = "HTML", disable_notification: bool = False):
    """Send text message to user on Telegram with HTML parse mode."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[Telegram] Missing token or chat id.")
        return False

    url = f"{BASE_URL}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": parse_mode,
        "disable_notification": disable_notification,
        "disable_web_page_preview": False
    }
    data = urllib.parse.urlencode(payload).encode()
    
    try:
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req) as resp:
            res_data = json.loads(resp.read().decode())
            return res_data.get("ok", False)
    except Exception as e:
        print(f"[Telegram Notice] HTML send failed ({e}), falling back to plain text...")
        try:
            payload.pop("parse_mode", None)
            plain_data = urllib.parse.urlencode(payload).encode()
            req = urllib.request.Request(url, data=plain_data)
            with urllib.request.urlopen(req) as resp:
                return json.loads(resp.read().decode()).get("ok", False)
        except Exception as e2:
            print(f"[Telegram Error] Plain send failed: {e2}")
            return False

def send_document(file_path: Path, caption: str = ""):
    """Send a PDF file (e.g. tailored resume) to Telegram with a caption."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    
    import requests
    url = f"{BASE_URL}/sendDocument"
    try:
        with open(file_path, "rb") as f:
            files = {"document": (file_path.name, f, "application/pdf")}
            data = {
                "chat_id": TELEGRAM_CHAT_ID,
                "caption": caption[:1024],
                "parse_mode": "HTML"
            }
            res = requests.post(url, data=data, files=files, timeout=30)
            return res.json().get("ok", False)
    except Exception as e:
        print(f"[Telegram Error] send_document failed: {e}")
        return False

def notify_job_found(
    job: dict,
    match_score: int,
    email_sent: bool,
    hr_email: str = None,
    recruiter_name: str = None,
    recruiter_headline: str = None,
    recruiter_profile: str = None,
    pdf_path: Path = None,
    cover_letter_pdf: Path = None
):
    """Format and send an advanced job notification card with 1-click apply link, recruiter intel, and dual PDFs."""
    company = html.escape(job.get("company", "Unknown Company"))
    title = html.escape(job.get("title", "Software Engineer"))
    location = html.escape(job.get("location", "Location Not Specified"))
    apply_url = job.get("url", "#")
    
    msg = (
        f"🎯 <b>NEW JOB MATCH (Score: {match_score}%)</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"🏢 <b>Company:</b> {company}\n"
        f"💼 <b>Role:</b> {title}\n"
        f"📍 <b>Location:</b> {location}\n"
        f"📊 <b>ATS Fit:</b> {match_score}/100\n"
    )

    if recruiter_name:
        msg += f"👤 <b>Recruiter:</b> {html.escape(recruiter_name)}\n"
        if recruiter_headline and recruiter_headline != "Hiring Team":
            msg += f"🏷️ <b>Title:</b> <i>{html.escape(recruiter_headline)}</i>\n"
        if recruiter_profile:
            msg += f"🔗 <b>LinkedIn Profile:</b> <a href=\"{recruiter_profile}\">View Recruiter</a>\n"

    if email_sent and hr_email:
        msg += f"📬 <b>Status:</b> ✅ Outreach Delivered to <code>{html.escape(hr_email)}</code>\n"
    else:
        msg += f"📬 <b>Status:</b> ℹ️ Direct Portal Application Ready (Zero Bounces)\n"

    # Generate tailored 300-char LinkedIn connection note if recruiter is known
    if recruiter_name:
        first_name = recruiter_name.split()[0].title()
        co_short = company.split()[0]
        note = (
            f"Hi {first_name}, I saw you're hiring for {title} at {co_short}. "
            f"As a final-year B.Tech CSE IoT student, SIH winner, and 2-yr Python/FastAPI engineer, "
            f"I'd love to connect and share my portfolio!"
        )
        msg += f"\n💬 <b>Recruiter Connection Note (Copy-Paste):</b>\n<code>{html.escape(note)}</code>\n"

    msg += (
        f"\n🚀 <b><a href=\"{apply_url}\">👉 TAP HERE TO APPLY INSTANTLY</a></b>\n"
        f"\n<i>Tailored resume &amp; cover letter PDFs attached below.</i>"
    )

    send_message(msg)
    
    if pdf_path and Path(pdf_path).exists():
        send_document(Path(pdf_path), caption=f"📄 Tailored Resume ({company})")
    if cover_letter_pdf and Path(cover_letter_pdf).exists():
        send_document(Path(cover_letter_pdf), caption=f"✉️ Matching Cover Letter ({company})")

def notify_inbox_reply(sender: str, subject: str, snippet: str, classification: str):
    """Send high priority alert when HR replies."""
    urgency_badge = "🚨 <b>INTERVIEW INVITATION / INQUIRY DETECTED!</b>" if classification in ["interview", "inquiry"] else "📩 <b>APPLICATION UPDATE</b>"
    
    clean_sender = html.escape(sender)
    clean_subject = html.escape(subject)
    clean_snippet = html.escape(snippet)
    
    msg = (
        f"{urgency_badge}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>From:</b> {clean_sender}\n"
        f"📌 <b>Subject:</b> {clean_subject}\n"
        f"🏷️ <b>Type:</b> {classification.upper()}\n\n"
        f"💬 <b>Preview:</b>\n<i>{clean_snippet}</i>\n\n"
        f"⏰ <b>Check your inbox to reply!</b>"
    )
    send_message(msg, disable_notification=False)
