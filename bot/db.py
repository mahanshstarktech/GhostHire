import sqlite3
from datetime import datetime, date
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "bot/ghosthire.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    # Jobs table
    c.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        company TEXT NOT NULL,
        location TEXT,
        url TEXT UNIQUE NOT NULL,
        source TEXT NOT NULL,
        score INTEGER DEFAULT 0,
        status TEXT DEFAULT 'discovered',
        discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        applied_at TIMESTAMP
    )
    """)

    # Applications table
    c.execute("""
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id TEXT UNIQUE NOT NULL,
        resume_pdf_path TEXT,
        cover_letter TEXT,
        hr_email TEXT,
        email_sent_at TIMESTAMP,
        email_status TEXT DEFAULT 'pending',
        telegram_alert_sent BOOLEAN DEFAULT 0,
        FOREIGN KEY(job_id) REFERENCES jobs(id)
    )
    """)

    # Email log table (for strict rate-limiting and anti-spam)
    c.execute("""
    CREATE TABLE IF NOT EXISTS email_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipient TEXT NOT NULL,
        domain TEXT NOT NULL,
        subject TEXT NOT NULL,
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT NOT NULL
    )
    """)

    # Inbox replies table
    c.execute("""
    CREATE TABLE IF NOT EXISTS inbox_replies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id TEXT UNIQUE NOT NULL,
        sender TEXT NOT NULL,
        subject TEXT NOT NULL,
        snippet TEXT,
        classification TEXT,
        received_at TIMESTAMP,
        alerted_at TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

def save_job(job_id, title, company, location, url, source, score=0):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("""
        INSERT INTO jobs (id, title, company, location, url, source, score)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET score=excluded.score
        """, (job_id, title, company, location, url, source, score))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving job: {e}")
        return False
    finally:
        conn.close()

def is_job_seen(job_id_or_url):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM jobs WHERE id = ? OR url = ?", (job_id_or_url, job_id_or_url))
    row = c.fetchone()
    conn.close()
    return row is not None

def get_emails_sent_today_count():
    conn = get_connection()
    c = conn.cursor()
    today_str = date.today().isoformat()
    c.execute("SELECT COUNT(*) FROM email_logs WHERE date(sent_at) = date(?) AND status = 'sent'", (today_str,))
    count = c.fetchone()[0]
    conn.close()
    return count

def get_domain_emails_this_week_count(domain):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
    SELECT COUNT(*) FROM email_logs 
    WHERE domain = ? AND status = 'sent' AND sent_at >= datetime('now', '-7 days')
    """, (domain,))
    count = c.fetchone()[0]
    conn.close()
    return count

def log_email_sent(recipient, domain, subject, status="sent"):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
    INSERT INTO email_logs (recipient, domain, subject, status)
    VALUES (?, ?, ?, ?)
    """, (recipient, domain, subject, status))
    conn.commit()
    conn.close()

def update_job_status(job_id, status):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE jobs SET status = ? WHERE id = ?", (status, job_id))
    conn.commit()
    conn.close()

def save_application(job_id, resume_pdf_path, cover_letter, hr_email, email_status="sent"):
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute("""
    INSERT INTO applications (job_id, resume_pdf_path, cover_letter, hr_email, email_sent_at, email_status, telegram_alert_sent)
    VALUES (?, ?, ?, ?, ?, ?, 1)
    ON CONFLICT(job_id) DO UPDATE SET
        resume_pdf_path=excluded.resume_pdf_path,
        cover_letter=excluded.cover_letter,
        hr_email=excluded.hr_email,
        email_sent_at=excluded.email_sent_at,
        email_status=excluded.email_status,
        telegram_alert_sent=1
    """, (job_id, str(resume_pdf_path), cover_letter, hr_email, now, email_status))
    conn.commit()
    conn.close()

def is_reply_recorded(message_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM inbox_replies WHERE message_id = ?", (message_id,))
    row = c.fetchone()
    conn.close()
    return row is not None

def record_reply(message_id, sender, subject, snippet, classification):
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute("""
    INSERT INTO inbox_replies (message_id, sender, subject, snippet, classification, received_at, alerted_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (message_id, sender, subject, snippet, classification, now, now))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("GhostHire Database initialized at", DB_PATH)
