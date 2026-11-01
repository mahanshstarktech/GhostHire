import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import time
import argparse
from datetime import datetime
from bot.config import MIN_MATCH_SCORE, MIN_DELAY_BETWEEN_EMAILS_SECONDS
from bot.db import (
    init_db,
    save_job,
    update_job_status,
    save_application,
    get_emails_sent_today_count
)
from bot.scrapers import get_all_new_jobs
from bot.matcher import score_job
from bot.resume_generator import generate_tailored_resume, generate_cover_letter
from bot.hr_finder import get_target_hr_emails
from bot.mailer import send_application_email
from bot.inbox_monitor import check_inbox_for_replies
from bot.telegram_notifier import notify_job_found, send_message

def run_job_cycle():
    """Runs a single pass of job searching, tailoring, emailing, and notifying."""
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🔍 Starting GhostHire discovery cycle...")
    
    new_jobs = get_all_new_jobs()
    print(f"[*] Found {len(new_jobs)} unseen postings across portals.")
    
    processed_count = 0
    matched_count = 0
    
    for job in new_jobs:
        title = job["title"]
        company = job["company"]
        url = job["url"]
        j_id = job["id"]
        
        score, matched_kw = score_job(title, job.get("description", ""))
        save_job(j_id, title, company, job["location"], url, job["source"], score)
        processed_count += 1
        
        if score < MIN_MATCH_SCORE:
            print(f"  [-] Skipped low score: {company} | {title} (Score: {score}%)")
            continue
            
        matched_count += 1
        print(f"\n  🎯 High match: {company} — {title} (Score: {score}%)")
        print(f"     Matched: {', '.join(matched_kw)}")
        
        # Tailor LaTeX resume and compile PDF
        print(f"     [+] Compiling tailored LaTeX resume...")
        pdf_path = generate_tailored_resume(j_id, company, title, matched_kw)
        
        # Generate clean cover letter
        cover_letter = generate_cover_letter(company, title, matched_kw)
        
        # Discover and verify MX records for hiring team
        hr_candidates = get_target_hr_emails(company, url)
        target_hr = hr_candidates[0] if hr_candidates else None
        
        # Safe cold outreach (only if domain has verified MX records)
        email_sent = False
        if target_hr:
            subject = f"Application: {title} — Mahansh Gaur"
            success, msg = send_application_email(target_hr, subject, cover_letter, pdf_path)
            if success:
                email_sent = True
                print(f"     [+] Cold email delivered to verified inbox: {target_hr}")
            else:
                print(f"     [!] Outreach notice: {msg}")
        else:
            print(f"     [i] No public MX-verified email for {company}. Ready for direct portal apply.")
                
        # Record application
        save_application(
            job_id=j_id,
            resume_pdf_path=pdf_path,
            cover_letter=cover_letter,
            hr_email=target_hr if email_sent else None,
            email_status="sent" if email_sent else "skipped"
        )
        update_job_status(j_id, "applied" if email_sent else "notified")
        
        # Send Telegram Card
        print(f"     [+] Sending Telegram notification...")
        notify_job_found(
            job=job,
            match_score=score,
            email_sent=email_sent,
            hr_email=target_hr if email_sent else None,
            pdf_path=pdf_path
        )
        
        time.sleep(MIN_DELAY_BETWEEN_EMAILS_SECONDS)
        
        # Maximum 5 applications per cycle to stay well under rate limits
        if matched_count >= 5:
            print("[*] Reached cycle limit (5 high-match applications). Pausing.")
            break

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ Discovery cycle finished. Scanned: {processed_count}, Matched: {matched_count}")

def run_inbox_cycle():
    """Checks Gmail inbox for replies from companies or recruiters."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 📬 Checking inbox for recruiter responses...")
    check_inbox_for_replies()

def main():
    parser = argparse.ArgumentParser(description="GhostHire: Autonomous 24/7 AI Job Hunter")
    parser.add_argument("--once", action="store_true", help="Run a single pass and exit")
    parser.add_argument("--daemon", action="store_true", help="Run continuous scheduled loop")
    args = parser.parse_args()

    init_db()

    if args.once:
        run_inbox_cycle()
        run_job_cycle()
        return

    import schedule
    
    print("🚀 GhostHire 24/7 Agent is running in daemon mode!")
    send_message("👻 <b>GhostHire 24/7 Agent Online!</b>\nScanning job boards, tailoring resumes, and monitoring inbox.")
    
    run_inbox_cycle()
    run_job_cycle()

    schedule.every(15).minutes.do(run_inbox_cycle)
    schedule.every(2).hours.do(run_job_cycle)

    while True:
        schedule.run_pending()
        time.sleep(30)

if __name__ == "__main__":
    main()
