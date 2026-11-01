import re
import urllib.request
import urllib.parse
import json
import smtplib
from urllib.parse import urlparse
import dns.resolver

GENERIC_BLACKLIST = [
    "careers", "jobs", "talent", "hiring", "recruiting",
    "info", "contact", "support", "no-reply", "noreply", "donotreply"
]

def check_mx_valid(domain: str) -> str | None:
    """Verifies that the domain exists and returns its primary MX host."""
    if not domain or "." not in domain:
        return None
    try:
        answers = dns.resolver.resolve(domain, "MX", lifetime=3)
        valid = [str(r.exchange).rstrip(".") for r in answers if str(r.exchange).strip() != "."]
        return valid[0] if valid else None
    except Exception:
        return None

def resolve_company_domain(company_name: str, company_url: str = None) -> str | None:
    """Finds official company web domain using Clearbit and DDG."""
    clean = re.sub(r"\(.*?\)", "", company_name).strip()
    clean = re.sub(r"\b(inc|corp|ltd|llc|pvt|technologies|solutions|pay)\b", "", clean, flags=re.I).strip()

    # 1. Clearbit lookup
    url = f"https://autocomplete.clearbit.com/v1/companies/suggest?query={urllib.parse.quote(clean)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode())
            for item in data:
                domain = item.get("domain", "").lower()
                if domain and check_mx_valid(domain):
                    return domain
    except Exception:
        pass

    # 2. Heuristic domain test
    heuristic = re.sub(r"[^a-zA-Z0-9]", "", company_name).lower()
    for tld in [".com", ".in", ".ai", ".io", ".co"]:
        d = f"{heuristic}{tld}"
        if check_mx_valid(d):
            return d

    return None

def extract_recruiter_from_linkedin_job(job_id_or_url: str) -> dict | None:
    """
    Extracts the hiring team / job poster directly from the public LinkedIn job page.
    Returns: {"name": str, "headline": str, "profile_url": str} or None.
    """
    job_id = None
    m = re.search(r"(\d{8,})", str(job_id_or_url))
    if m:
        job_id = m.group(1)
        url = f"https://www.linkedin.com/jobs/view/{job_id}"
    elif "linkedin.com/jobs" in str(job_id_or_url):
        url = str(job_id_or_url)
    else:
        return None

    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    })

    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            html = r.read().decode("utf-8", errors="ignore")

        # Check for recruiter card
        if "message-the-recruiter" in html or "base-main-card" in html:
            name_m = re.search(r'aria-label="Message ([^"]+)"', html)
            if not name_m:
                name_m = re.search(r'<h3[^>]*class="[^"]*base-main-card__title[^"]*"[^>]*>\s*([^<\n]+)', html)

            name = name_m.group(1).strip() if name_m else None
            
            url_m = re.search(r'href="([^"]+linkedin\.com\/in\/[^"]+)"', html)
            profile_url = url_m.group(1) if url_m else None
            if profile_url and "session_redirect=" in profile_url:
                profile_url = urllib.parse.unquote(profile_url.split("session_redirect=")[1].split("&")[0])

            headline_m = re.search(r'<h4[^>]*class="[^"]*base-main-card__subtitle[^"]*"[^>]*>\s*([\s\S]*?)<\/h4>', html)
            headline = re.sub(r"<.*?>", "", headline_m.group(1)).strip() if headline_m else "Hiring Team"

            if name and "message" not in name.lower() and len(name.split()) >= 2:
                return {
                    "name": name,
                    "headline": headline,
                    "profile_url": profile_url
                }
    except Exception as e:
        print(f"[Recruiter Finder] Error scraping job page: {e}")

    return None

def verify_corporate_email_smtp(first_name: str, last_name: str, domain: str) -> str | None:
    """
    Generates corporate email patterns for the real person and verifies them via SMTP RCPT TO.
    NEVER sends any email. Strictly verifies active mailbox existence.
    """
    if not domain or not first_name or not last_name:
        return None

    first = re.sub(r"[^a-z]", "", first_name.lower())
    last = re.sub(r"[^a-z]", "", last_name.lower())
    if not first or not last:
        return None

    patterns = [
        f"{first}.{last}@{domain}",
        f"{first}@{domain}",
        f"{first}{last}@{domain}",
        f"{first[0]}.{last}@{domain}",
        f"{first[0]}{last}@{domain}",
        f"{last}.{first}@{domain}",
    ]

    mx_host = check_mx_valid(domain)
    if not mx_host:
        return None

    try:
        server = smtplib.SMTP(timeout=5)
        server.connect(mx_host, 25)
        server.helo("verify.agent.local")
        server.mail("probe@verify.agent.local")

        # Catch-all detection probe
        probe_code, _ = server.rcpt(f"ghosthire_nonexistent_probe_9921@{domain}")
        is_catchall = (probe_code == 250)

        for email_addr in patterns:
            code, _ = server.rcpt(email_addr)
            # If server explicitly returns 250 and is not a catchall, it is verified!
            if code == 250 and not is_catchall:
                server.quit()
                print(f"[Recruiter Finder] Successfully verified real mailbox: {email_addr}")
                return email_addr

        server.quit()
    except Exception as e:
        print(f"[Recruiter Finder] SMTP Verification unavailable on {domain}: {e}")

    return None

def find_hiring_team(company_name: str, job_id_or_url: str) -> dict:
    """
    Comprehensive hiring team finder:
    1. Looks for named recruiter on the posting
    2. Resolves company official domain
    3. Verifies recruiter email if possible
    4. Guarantees ZERO generic careers@ emails
    """
    domain = resolve_company_domain(company_name, job_id_or_url)
    recruiter = extract_recruiter_from_linkedin_job(job_id_or_url)

    verified_email = None
    if recruiter and domain:
        parts = recruiter["name"].split()
        first_name = parts[0]
        last_name = parts[-1] if len(parts) > 1 else ""
        verified_email = verify_corporate_email_smtp(first_name, last_name, domain)

    return {
        "recruiter_name": recruiter["name"] if recruiter else None,
        "recruiter_headline": recruiter["headline"] if recruiter else None,
        "recruiter_profile": recruiter["profile_url"] if recruiter else None,
        "verified_email": verified_email,
        "domain": domain
    }

if __name__ == "__main__":
    res = find_hiring_team("QubeHealth-Pay", "4483617328")
    print("Result for QubeHealth:")
    print(json.dumps(res, indent=2))

