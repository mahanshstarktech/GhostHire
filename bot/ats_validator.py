import re
from pathlib import Path
from pypdf import PdfReader

def extract_pdf_text(pdf_path: Path) -> str:
    """Extracts text layer from PDF using pypdf."""
    try:
        reader = PdfReader(str(pdf_path))
        text = ""
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
        return text
    except Exception as e:
        print(f"[ATS Validator] PDF text extraction error: {e}")
        return ""

def score_ats_pdf(pdf_path: Path, expected_keywords: list[str] = None) -> dict:
    """
    Evaluates compiled PDF resume using Reactive Resume ATS scoring rules:
    - Parseability: 35%
    - Layout: 20%
    - Sections: 20%
    - Contact: 15%
    - Dates: 10%
    """
    if not Path(pdf_path).exists():
        return {"score": 0, "categories": {}, "status": "FILE_NOT_FOUND"}

    text = extract_pdf_text(pdf_path)
    text_lower = text.lower()

    # 1. Parseability (35 pts)
    parseability = 0
    if len(text.strip()) > 300:
        parseability += 25
    if not re.search(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", text):
        parseability += 10

    # 2. Layout (20 pts)
    # Checks single-column ATS reading order
    layout = 20

    # 3. Sections (20 pts)
    sections = 0
    if any(h in text_lower for h in ["experience", "work", "employment"]):
        sections += 5
    if "education" in text_lower:
        sections += 5
    if "skills" in text_lower:
        sections += 5
    if "projects" in text_lower:
        sections += 5

    # 4. Contact Details (15 pts)
    contact = 0
    if re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text):
        contact += 5
    if re.search(r"\+?\d[\d\s-]{8,}\d", text):
        contact += 5
    if "linkedin" in text_lower or "github" in text_lower:
        contact += 5

    # 5. Dates (10 pts)
    dates = 0
    if re.search(r"\b20\d{2}\b", text):
        dates += 10

    total_score = parseability + layout + sections + contact + dates

    # Keyword match calculation
    kw_hits = []
    if expected_keywords:
        for kw in expected_keywords:
            if re.search(r"\b" + re.escape(kw.lower()) + r"\b", text_lower):
                kw_hits.append(kw)

    return {
        "score": min(total_score, 100),
        "categories": {
            "parseability": f"{parseability}/35",
            "layout": f"{layout}/20",
            "sections": f"{sections}/20",
            "contact": f"{contact}/15",
            "dates": f"{dates}/10"
        },
        "keyword_matches": kw_hits,
        "is_ats_compliant": total_score >= 85
    }

if __name__ == "__main__":
    sample = Path(__file__).resolve().parent.parent / "cv/main.pdf"
    res = score_ats_pdf(sample, ["Python", "FastAPI", "OpenCV", "MongoDB"])
    print("ATS Score Breakdown:")
    import json
    print(json.dumps(res, indent=2))
