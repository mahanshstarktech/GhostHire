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
    is_job_seen,
    get_emails_sent_today_count
)
from bot.scrapers import get_all_new_jobs
from bot.matcher import score_job
from bot.resume_generator import (
    generate_tailored_resume,
    generate_cover_letter_pdf,
    generate_cover_letter
)
from bot.ats_validator import score_ats_pdf
from bot.recruiter_finder import find_hiring_team
from bot.mailer import send_application_email
from bot.inbox_monitor import check_inbox_for_replies
from bot.telegram_notifier import notify_job_found, send_message

def run_job_cycle():
    """Runs a single pass of job searching, tailoring, outreach, and notifying."""
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
        
        # Check fuzzy company + title deduplication
        if is_job_seen(j_id, company=company, title=title) or is_job_seen(url, company=company, title=title):
            continue

        score, matched_kw = score_job(title, job.get("description", ""))
        save_job(j_id, title, company, job["location"], url, job["source"], score)
        processed_count += 1
        
        if score < MIN_MATCH_SCORE:
            print(f"  [-] Skipped low score: {company} | {title} (Score: {score}%)")
            continue
            
        matched_count += 1
        print(f"\n  🎯 High match: {company} — {title} (Score: {score}%)")
        print(f"     Matched: {', '.join(matched_kw)}")
        
        # 1. Investigate real recruiters & verified email for the company first
        print(f"     [+] Investigating real recruiters & verified email for {company}...")
        intel = find_hiring_team(company, url)
        
        recruiter_name = intel.get("recruiter_name")
        recruiter_headline = intel.get("recruiter_headline")
        recruiter_profile = intel.get("recruiter_profile")
        verified_email = intel.get("verified_email")
        
        if recruiter_name:
            print(f"     [👤] Discovered Real Recruiter: {recruiter_name} ({recruiter_headline})")
        if verified_email:
            print(f"     [✉️] 100% Verified Active Mailbox: {verified_email}")
        else:
            print(f"     [ℹ️] No direct verified individual mailbox. Safe Mode: skipping blind email to protect sender score.")

        # 2. Compile bespoke LuaLaTeX resume and companion cover letter PDF
        print(f"     [+] Compiling tailored LaTeX resume & cover letter PDFs...")
        pdf_path = generate_tailored_resume(j_id, company, title, matched_kw)
        cover_pdf_path = generate_cover_letter_pdf(
            j_id, company, title, matched_kw,
            recruiter_name=recruiter_name,
            recruiter_headline=recruiter_headline,
            location=job.get("location")
        )

        # 3. Validate ATS Compliance via Reactive Resume Rule Engine
        ats_eval = score_ats_pdf(pdf_path, matched_kw)
        print(f"     [📊] ATS Score: {ats_eval.get('score')}/100 (Compliant: {ats_eval.get('is_ats_compliant')})")

        # 4. Generate cover letter personalized directly to the recruiter
        cover_letter_text = generate_cover_letter(company, title, matched_kw, recruiter_name=recruiter_name)
        
        # 5. Safe cold outreach ONLY to verified real email addresses (Zero generic careers@)
        email_sent = False
        if verified_email:
            subject = f"Application: {title} — Mahansh Gaur"
            success, msg = send_application_email(
                verified_email,
                subject,
                cover_letter_text,
                resume_pdf_path=pdf_path,
                cover_letter_pdf_path=cover_pdf_path
            )
            if success:
                email_sent = True
                print(f"     [+] Delivered cold email directly to {recruiter_name} ({verified_email})")
            else:
                print(f"     [!] Outreach notice: {msg}")
                
        # 6. Record in local database
        save_application(
            job_id=j_id,
            resume_pdf_path=pdf_path,
            cover_letter=cover_letter_text,
            hr_email=verified_email if email_sent else None,
            email_status="sent" if email_sent else "skipped"
        )
        update_job_status(j_id, "applied" if email_sent else "notified")
        
        # 7. Send Rich Telegram Card with Recruiter intel, Connection Note & DUAL PDF attachments
        print(f"     [+] Delivering Telegram intelligence card with dual PDFs...")
        notify_job_found(
            job=job,
            match_score=score,
            email_sent=email_sent,
            hr_email=verified_email,
            recruiter_name=recruiter_name,
            recruiter_headline=recruiter_headline,
            recruiter_profile=recruiter_profile,
            pdf_path=pdf_path,
            cover_letter_pdf=cover_pdf_path
        )
        
        if email_sent:
            time.sleep(MIN_DELAY_BETWEEN_EMAILS_SECONDS)
        
        # Limit to 5 per cycle
        if matched_count >= 5:
            print("[*] Reached cycle limit (5 high-match opportunities). Pausing.")
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
    send_message("👻 <b>GhostHire Agent Upgraded & Active!</b>\nReal recruiter intelligence, zero-bounce verification, and 1-tap connection notes enabled.")
    
    run_inbox_cycle()
    run_job_cycle()

    schedule.every(15).minutes.do(run_inbox_cycle)
    schedule.every(2).hours.do(run_job_cycle)

    while True:
        schedule.run_pending()
        time.sleep(30)

if __name__ == "__main__":
    main()
