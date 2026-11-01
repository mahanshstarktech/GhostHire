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

def make_pdf_filename(company: str, job_title: str) -> str:
    """Generate a unique, professional PDF filename like Mahansh_Gaur_Resume_Vahan_AI.pdf"""
    candidate_prefix = clean_name(CANDIDATE_NAME)
    co = re.sub(r"[^a-zA-Z0-9]", "_", company).strip("_")
    co = re.sub(r"_+", "_", co)
    return f"{candidate_prefix}_Resume_{co}.pdf"

def generate_tailored_resume(job_id: str, company: str, job_title: str, matched_keywords: list[str]) -> Path:
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
    
    if compiled_pdf.exists():
        final_name = make_pdf_filename(company, job_title)
        final_pdf = out_dir / final_name
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
        fallback_pdf = CV_DIR / "main.pdf"
        return fallback_pdf

def generate_cover_letter(company: str, job_title: str, matched_keywords: list[str], recruiter_name: str = None) -> str:
    """
    Generates a personalized, professional cold email body.
    If recruiter_name is provided, addresses them directly by first name!
    """
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

I have attached my resume for your review. I would welcome the opportunity to discuss how I can contribute to {company}'s engineering goals.

Best regards,
{CANDIDATE_NAME}
Jaipur, Rajasthan, India | {CANDIDATE_PHONE}
LinkedIn: {CANDIDATE_LINKEDIN}
GitHub: {CANDIDATE_GITHUB}"""
    return letter
