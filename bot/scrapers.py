import subprocess
import json
from pathlib import Path
from bot.config import LINKEDIN_CLI, FREEHIRE_CLI
from bot.db import is_job_seen

LINKEDIN_SEARCHES = [
    {"q": "Software Engineer Intern", "l": "India", "age": 7},
    {"q": "AI Engineer Intern", "l": "India", "age": 7},
    {"q": "Full Stack Developer", "l": "India", "age": 7},
    {"q": "Python Developer", "l": "India", "age": 7},
    {"q": "IoT Engineer", "l": "India", "age": 14},
    {"q": "Software Engineer Intern", "l": "Remote", "age": 7},
    {"q": "AI Engineer", "l": "Remote", "age": 7},
]

FREEHIRE_QUERIES = [
    "Python",
    "IoT",
    "Computer Vision",
    "FastAPI"
]

def scrape_linkedin_jobs(limit_per_search: int = 5) -> list[dict]:
    """Scrapes LinkedIn guest job listings using the self-contained CLI."""
    jobs = []
    for s in LINKEDIN_SEARCHES:
        cmd = [
            "bun", "run", str(LINKEDIN_CLI), "search",
            "-q", s["q"],
            "-l", s["l"],
            "--jobage", str(s["age"]),
            "--limit", str(limit_per_search),
            "--format", "json"
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
            if res.returncode == 0:
                data = json.loads(res.stdout)
                for item in data.get("results", []):
                    j_id = f"li_{item.get('id')}"
                    url = item.get("url", "")
                    if not is_job_seen(j_id) and not is_job_seen(url):
                        jobs.append({
                            "id": j_id,
                            "title": item.get("title", ""),
                            "company": item.get("company", ""),
                            "location": item.get("location", ""),
                            "url": url,
                            "source": "LinkedIn",
                            "description": ""
                        })
        except Exception as e:
            print(f"[GhostHire Scraper] LinkedIn search error ('{s['q']}'): {e}")
    return jobs

def scrape_freehire_jobs(limit_per_query: int = 4) -> list[dict]:
    """Scrapes Freehire tech aggregator listings using self-contained CLI."""
    jobs = []
    for q in FREEHIRE_QUERIES:
        cmd = [
            "bun", "run", str(FREEHIRE_CLI), "search",
            "--query", q,
            "--limit", str(limit_per_query),
            "--format", "json"
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=25)
            if res.returncode == 0:
                data = json.loads(res.stdout)
                for item in data.get("results", []):
                    j_id = f"fh_{item.get('id')}"
                    url = item.get("url", "")
                    if not is_job_seen(j_id) and not is_job_seen(url):
                        jobs.append({
                            "id": j_id,
                            "title": item.get("title", ""),
                            "company": item.get("company", ""),
                            "location": item.get("location", ""),
                            "url": url,
                            "source": "Freehire",
                            "description": item.get("description", "")
                        })
        except Exception as e:
            print(f"[GhostHire Scraper] Freehire search error ('{q}'): {e}")
    return jobs

def get_all_new_jobs() -> list[dict]:
    """Gathers all fresh unseen jobs from all portals."""
    all_jobs = []
    all_jobs.extend(scrape_linkedin_jobs())
    all_jobs.extend(scrape_freehire_jobs())
    return all_jobs

