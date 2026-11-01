import os
import re
import subprocess
from pathlib import Path
from bot.config import (
    BASE_DIR,
    LUALATEX_PATH,
    CANDIDATE_NAME,
    CANDIDATE_PHONE,
    CANDIDATE_LINKEDIN,
    CANDIDATE_GITHUB
)

CV_DIR = BASE_DIR / "cv"
MASTER_TEX = CV_DIR / "main.tex"
APPS_DIR = BASE_DIR / "applications"

def clean_name(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "_", s).strip("_")

def make_pdf_filenames(company: str) -> tuple[str, str]:
    """Generate company-specific filenames for Resume and Cover Letter."""
    candidate_prefix = clean_name(CANDIDATE_NAME)
    co = re.sub(r"[^a-zA-Z0-9]", "_", company).strip("_")
    co = re.sub(r"_+", "_", co)
    resume_name = f"{candidate_prefix}_Resume_{co}.pdf"
    cover_name = f"{candidate_prefix}_Cover_Letter_{co}.pdf"
    return resume_name, cover_name

def generate_tailored_resume(job_id: str, company: str, job_title: str, matched_keywords: list[str]) -> Path:
    """Compiles bespoke single-page LaTeX resume with LuaLaTeX."""
    out_dir = APPS_DIR / f"{clean_name(company)}_{clean_name(job_id)}"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    tex_content = MASTER_TEX.read_text(encoding="utf-8")
    
    tailored_title = job_title.replace("&", r"\&")
    tex_content = re.sub(
        r"\\title\{[^}]*\}",
        f"\\\\title{{{tailored_title} --- Candidate Profile}}",
        tex_content,
        count=1
    )
    
    target_tex = out_dir / "resume.tex"
    target_tex.write_text(tex_content, encoding="utf-8")
    
    compiler = str(LUALATEX_PATH)
    cmd = [compiler, "-interaction=nonstopmode", "resume.tex"]
    proc = subprocess.run(cmd, cwd=out_dir, capture_output=True, text=True)
    
    compiled_pdf = out_dir / "resume.pdf"
    resume_name, _ = make_pdf_filenames(company)
    final_pdf = out_dir / resume_name
    
    if compiled_pdf.exists():
        if final_pdf != compiled_pdf:
            if final_pdf.exists():
                final_pdf.unlink()
            compiled_pdf.rename(final_pdf)
        
        for ext in [".aux", ".log", ".out"]:
            f = out_dir / f"resume{ext}"
            if f.exists():
                try:
                    f.unlink()
                except Exception:
                    pass
        return final_pdf
    else:
        print(f"[Resume Generator Error] Compilation failed for {company}:\n{proc.stdout[-400:]}")
        return CV_DIR / "main.pdf"

def generate_cover_letter_pdf(
    job_id: str,
    company: str,
    job_title: str,
    matched_keywords: list[str],
    recruiter_name: str = None,
    recruiter_headline: str = None,
    location: str = None
) -> Path:
    """Compiles matching executive Cover Letter PDF using ModernCV."""
    out_dir = APPS_DIR / f"{clean_name(company)}_{clean_name(job_id)}"
    out_dir.mkdir(parents=True, exist_ok=True)

    first_last = CANDIDATE_NAME.split()
    first_name = first_last[0] if first_last else "Mahansh"
    last_name = first_last[-1] if len(first_last) > 1 else "Gaur"

    if recruiter_name:
        salutation = f"Dear {recruiter_name.split()[0].title()},"
        recipient_line = f"{recruiter_name}, {recruiter_headline or 'Hiring Team'}"
    else:
        salutation = f"Dear {company} Hiring Team,"
        recipient_line = f"{company} Hiring Team"

    loc_str = location or "India"
    recipient_address = f"{company}, {loc_str}".replace("&", r"\&")
    safe_title = job_title.replace("&", r"\&")
    safe_company = company.replace("&", r"\&")

    kw_list = ", ".join(matched_keywords[:4]) if matched_keywords else "Python, FastAPI, and Distributed Systems"
    safe_kw = kw_list.replace("&", r"\&")

    cover_tex = f"""\\documentclass[11pt,a4paper,sans]{{moderncv}}
\\moderncvstyle{{banking}}
\\moderncvcolor{{blue}}
\\nopagenumbers{{}}

\\usepackage[scale=0.82]{{geometry}}

\\name{{{first_name}}}{{{last_name}}}
\\title{{Cover Letter}}
\\address{{Jaipur, Rajasthan, India}}{{}}
\\phone[mobile]{{{CANDIDATE_PHONE}}}
\\email{{{CANDIDATE_NAME.lower().replace(' ', '')}@gmail.com}}
\\social[linkedin]{{mahansh-gaur}}
\\social[github]{{mahanshstarktech}}

\\begin{{document}}
\\recipient{{{recipient_line}}}{{{recipient_address}}}
\\date{{\\today}}
\\opening{{{salutation}}}
\\closing{{Sincerely,}}
\\enclosure[Attached]{{Resume}}

\\makelettertitle

I am writing to express my strong enthusiasm for the \\textbf{{{safe_title}}} role at \\textbf{{{safe_company}}}. As a final-year B.Tech student in Computer Science \\& Engineering (IoT) graduating in 2027 and winner of the Smart India Hackathon (SIH) 2025, I bring hands-on experience designing production-grade backend systems, automated ingestion pipelines, and rigorous test automation suites.

Throughout my engineering work, I have focused on building measurable, high-availability software architectures:
\\begin{{itemize}}
    \\item \\textbf{{AI Backend \\& Async Pipelines:}} Engineered an end-to-end product ingestion pipeline using FastAPI, Celery, Redis, and MongoDB with structured Gemini outputs, automated deduplication, and rate-limit resilience.
    \\item \\textbf{{Computer Vision \\& Embedded Robotics:}} Designed an autonomous 6-DOF pick-and-place robotic arm system with OpenCV color segmentation and visual servoing, slashing memory footprint by 75\\% on Raspberry Pi 4B.
    \\item \\textbf{{Testing \\& CI/CD Systems:}} Architected AmitAstro with 170+ automated tests across Vitest, Supertest, and Playwright, validating cross-database behavior (SQLite \\& PostgreSQL) via GitHub Actions CI service containers.
\\end{{itemize}}

My core competencies in {safe_kw} directly align with {safe_company}'s engineering objectives. I thrive in high-ownership engineering environments and look forward to contributing immediately to your team.

Thank you for your time and consideration. I welcome the opportunity to discuss my qualifications in an interview.

\\makeletterclosing
\\end{{document}}
"""

    target_tex = out_dir / "cover_letter.tex"
    target_tex.write_text(cover_tex, encoding="utf-8")

    compiler = str(LUALATEX_PATH)
    cmd = [compiler, "-interaction=nonstopmode", "cover_letter.tex"]
    proc = subprocess.run(cmd, cwd=out_dir, capture_output=True, text=True)

    compiled_pdf = out_dir / "cover_letter.pdf"
    _, cover_name = make_pdf_filenames(company)
    final_pdf = out_dir / cover_name

    if compiled_pdf.exists():
        if final_pdf != compiled_pdf:
            if final_pdf.exists():
                final_pdf.unlink()
            compiled_pdf.rename(final_pdf)

        for ext in [".aux", ".log", ".out"]:
            f = out_dir / f"cover_letter{ext}"
            if f.exists():
                try:
                    f.unlink()
                except Exception:
                    pass
        return final_pdf
    else:
        print(f"[Cover Letter Error] Compilation failed for {company}:\n{proc.stdout[-400:]}")
        return None

def generate_cover_letter(company: str, job_title: str, matched_keywords: list[str], recruiter_name: str = None) -> str:
    """Generates clean plain text cover letter for email body."""
    kw_str = ", ".join(matched_keywords[:4]) if matched_keywords else "Python, FastAPI, and Full-Stack Development"
    
    if recruiter_name and len(recruiter_name.split()) >= 1:
        first_name = recruiter_name.split()[0].title()
        greeting = f"Hi {first_name},"
    else:
        greeting = f"Hi {company} Hiring Team,"

    letter = f"""{greeting}

I came across your open role for {job_title} at {company} and wanted to reach out directly to express my strong interest.

I am a final-year B.Tech student in Computer Science & Engineering (IoT) graduating in 2027, winner of the Smart India Hackathon (SIH) 2025, with ~2 years of hands-on software development experience across production systems.

A few relevant highlights that align with your work:
• Production AI & Backend: Engineered an end-to-end AI product-listing pipeline using FastAPI, Celery, Redis, and MongoDB with structured Gemini outputs and rate-limit resilience.
• Computer Vision & Embedded: Developed autonomous 6-DOF robotic pick-and-place systems with OpenCV and visual servoing, optimizing memory footprint by 75% on Raspberry Pi.
• Full-Stack & Architecture: Built AmitAstro, an end-to-end consultation platform with 170+ automated tests across unit, integration, and security layers.

My technical background strongly aligns with {kw_str}.

I have attached my resume and cover letter for your review. I would welcome the opportunity to discuss how I can contribute to {company}'s engineering goals.

Best regards,
{CANDIDATE_NAME}
Jaipur, Rajasthan, India | {CANDIDATE_PHONE}
LinkedIn: {CANDIDATE_LINKEDIN}
GitHub: {CANDIDATE_GITHUB}"""
    return letter
