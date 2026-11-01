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

def notify_job_found(job: dict, match_score: int, email_sent: bool, hr_email: str = None, pdf_path: Path = None):
    """Format and send a job notification card with 1-click apply link."""
    status_text = "✅ <b>Cold Outreach Sent to Hiring Team</b>" if email_sent else "ℹ️ <b>Direct Portal Application Ready</b>"
    
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
        f"📊 <b>ATS Match:</b> {match_score}/100\n"
        f"📬 <b>Status:</b> {status_text}\n"
    )
    if hr_email:
        msg += f"👤 <b>Contacted:</b> <code>{html.escape(hr_email)}</code>\n"
        
    msg += (
        f"\n🚀 <b><a href=\"{apply_url}\">👉 TAP HERE TO APPLY INSTANTLY</a></b>\n"
        f"\n<i>Tailored resume PDF generated &amp; attached below.</i>"
    )

    send_message(msg)
    
    if pdf_path and Path(pdf_path).exists():
        send_document(Path(pdf_path), caption=f"📄 Tailored Resume for {company}")

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
