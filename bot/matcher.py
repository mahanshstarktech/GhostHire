import re

TARGET_KEYWORDS = {
    "python": 15,
    "fastapi": 12,
    "django": 10,
    "react": 10,
    "typescript": 8,
    "javascript": 8,
    "sql": 8,
    "postgresql": 8,
    "mongodb": 8,
    "redis": 6,
    "celery": 6,
    "opencv": 10,
    "computer vision": 10,
    "iot": 12,
    "machine learning": 10,
    "ai": 8,
    "llm": 8,
    "rest api": 8,
    "docker": 6,
    "git": 5,
}

ROLE_KEYWORDS = {
    "software engineer": 25,
    "software developer": 25,
    "sde": 25,
    "intern": 20,
    "internship": 20,
    "trainee": 18,
    "junior": 18,
    "entry level": 18,
    "ai engineer": 25,
    "ml engineer": 25,
    "full stack": 22,
    "backend": 22,
    "python developer": 25,
    "iot engineer": 25,
}

DISQUALIFIERS = [
    r"\b10\+\s*years\b",
    r"\b8\+\s*years\b",
    r"\b7\+\s*years\b",
    r"\bprincipal\b",
    r"\bstaff\b",
    r"\bdirector\b",
    r"\bvp\b",
    r"\bhead of\b",
    r"\bphd required\b",
    r"\bexecutive\b",
    r"\baccountant\b",
    r"\bnurse\b"
]

def score_job(title: str, description: str = "") -> tuple[int, list[str]]:
    """
    Scores a job title and description against target profile (0 to 100).
    Returns (score, matched_keywords).
    """
    text = f"{title.lower()} {description.lower()}"
    
    # Check for hard disqualifiers
    for pattern in DISQUALIFIERS:
        if re.search(pattern, text):
            return 0, ["Disqualified: Seniority/Non-tech"]

    matched = []
    score = 0
    
    # Check role title match
    for role, points in ROLE_KEYWORDS.items():
        if role in title.lower():
            score += points
            matched.append(role.title())
            break

    # Check skill keywords match
    for kw, points in TARGET_KEYWORDS.items():
        if re.search(r"\b" + re.escape(kw) + r"\b", text):
            score += points
            matched.append(kw)

    # Normalize score max to 100
    final_score = min(score, 100)
    
    # Baseline for relevant tech internships/entry roles
    if any(k in title.lower() for k in ["intern", "trainee", "junior", "sde", "software"]) and final_score < 65:
        final_score = max(final_score, 70)
        
    return final_score, matched

