import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import imaplib
import email
from email.header import decode_header
import re
from datetime import datetime
from bot.config import GMAIL_USER, GMAIL_APP_PASS
from bot.db import is_reply_recorded, record_reply
from bot.telegram_notifier import notify_inbox_reply

INTERVIEW_KEYWORDS = [
    r"\binterview\b",
    r"\binvitation\b",
    r"\bshortlist(ed)?\b",
    r"\bnext steps\b",
    r"\btechnical round\b",
    r"\bschedule a call\b",
    r"\bphone screen\b",
    r"\bassessment\b",
    r"\boffer\b",
    r"\bconversation\b"
]

REJECTION_KEYWORDS = [
    r"\bregret to inform\b",
    r"\bunfortunately\b",
    r"\bother candidates\b",
    r"\bnot moving forward\b",
    r"\bnot be proceeding\b"
]

def clean_header(val: str) -> str:
    if not val:
        return ""
    decoded_parts = decode_header(val)
    out = []
    for part, enc in decoded_parts:
        if isinstance(part, bytes):
            try:
                out.append(part.decode(enc or "utf-8", errors="ignore"))
            except Exception:
                out.append(part.decode("latin-1", errors="ignore"))
        else:
            out.append(str(part))
    return "".join(out)

def classify_email(subject: str, body: str) -> str:
    text = f"{subject.lower()} {body.lower()}"
    for pat in INTERVIEW_KEYWORDS:
        if re.search(pat, text):
            return "interview"
    for pat in REJECTION_KEYWORDS:
        if re.search(pat, text):
            return "rejection"
    if any(k in text for k in ["application", "resume", "cv", "candidacy", "interview"]):
        return "inquiry"
    return "other"

def check_inbox_for_replies():
    """
    Fast IMAP checker: inspects the latest 15 inbox messages for replies to applications.
    """
    if not GMAIL_USER or not GMAIL_APP_PASS:
        return

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_APP_PASS)
        mail.select("INBOX", readonly=True)
        
        status, data = mail.search(None, "ALL")
        if status != "OK" or not data or not data[0]:
            mail.logout()
            return

        msg_ids = data[0].split()
        latest_ids = msg_ids[-15:]

        for m_id in reversed(latest_ids):
            status, header_data = mail.fetch(m_id, "(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM MESSAGE-ID DATE)])")
            if status != "OK" or not header_data:
                continue

            msg = email.message_from_bytes(header_data[0][1])
            message_id = msg.get("Message-ID", str(m_id.decode()))
            
            if is_reply_recorded(message_id):
                continue

            subject = clean_header(msg.get("Subject", ""))
            sender = clean_header(msg.get("From", ""))

            subj_lower = subject.lower()
            is_potential_reply = any(k in subj_lower for k in [
                "application", "interview", "candidate", "role", "position",
                "hiring", "resume", "cv", "round", "call", "mahansh"
            ])

            if not is_potential_reply:
                record_reply(message_id, sender, subject, "", "unrelated")
                continue

            status, body_data = mail.fetch(m_id, "(BODY.PEEK[TEXT])")
            body_text = ""
            if status == "OK" and body_data:
                try:
                    body_text = body_data[0][1].decode(errors="ignore")[:500]
                except Exception:
                    pass

            classification = classify_email(subject, body_text)
            snippet = body_text.strip()[:300].replace("\n", " ")
            record_reply(message_id, sender, subject, snippet, classification)

            if classification in ["interview", "inquiry"]:
                notify_inbox_reply(sender, subject, snippet, classification)
                print(f"[GhostHire Inbox Alert] Interview/Inquiry detected from {sender}!")

        mail.logout()
    except Exception as e:
        print(f"[GhostHire Inbox Error] {e}")

if __name__ == "__main__":
    check_inbox_for_replies()
