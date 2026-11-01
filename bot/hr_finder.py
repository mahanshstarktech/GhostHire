import re
import urllib.request
import urllib.parse
import json
from urllib.parse import urlparse
import dns.resolver

GENERIC_PREFIXES = ["careers", "jobs", "talent", "hiring", "recruiting", "hr"]

def check_mx_valid(domain: str) -> bool:
    """Verifies that the domain exists and has functional mail exchange (MX) servers."""
    if not domain or "." not in domain:
        return False
    try:
        answers = dns.resolver.resolve(domain, "MX", lifetime=3)
        valid_mx = [str(r.exchange).rstrip(".") for r in answers if str(r.exchange).strip() != "."]
        return len(valid_mx) > 0
    except Exception:
        return False

def find_domain_via_clearbit(company_name: str) -> str | None:
    """Uses Clearbit Company Autocomplete API to find official company domain."""
    clean = re.sub(r"\(.*?\)", "", company_name).strip()
    clean = re.sub(r"\b(inc|corp|ltd|llc|pvt|technologies|solutions|pay)\b", "", clean, flags=re.I).strip()
    
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
    return None

def find_domain_via_ddg_instant(company_name: str) -> str | None:
    """Uses DuckDuckGo Instant Answer API to find official company website."""
    url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(company_name)}&format=json"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode())
            results = data.get("Results", [])
            for res in results:
                u = res.get("FirstURL", "")
                if u:
                    parsed = urlparse(u)
                    domain = re.sub(r"^www\.", "", parsed.netloc.lower())
                    if domain and check_mx_valid(domain):
                        return domain
    except Exception:
        pass
    return None

def find_domains_via_ddg_html(company_name: str) -> list[str]:
    """Scrapes DuckDuckGo HTML search results for company domains."""
    url = "https://html.duckduckgo.com/html/"
    data = urllib.parse.urlencode({"q": f"{company_name} official website careers"}).encode()
    req = urllib.request.Request(url, data=data, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })
    domains = []
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            urls = re.findall(r'class="result__url"[^>]*>\s*([^\s<]+)', html)
            skip = ["duckduckgo.com", "linkedin.com", "glassdoor.com", "indeed.com",
                    "naukri.com", "facebook.com", "twitter.com", "youtube.com", "instagram.com",
                    "wikipedia.org", "economictimes.indiatimes.com", "tracxn.com", "cbinsights.com"]
            for u in urls:
                clean_u = u.split("/")[0].strip().lower()
                clean_u = re.sub(r"^www\.", "", clean_u)
                if clean_u and not any(s in clean_u for s in skip):
                    if clean_u not in domains and check_mx_valid(clean_u):
                        domains.append(clean_u)
    except Exception:
        pass
    return domains

def get_target_hr_emails(company_name: str, company_url: str = None) -> list[str]:
    """
    Intelligently finds and returns VALID HR email addresses.
    STRICT RULE: Only returns emails for domains that pass check_mx_valid!
    """
    candidates_domains = []

    # 1. Clearbit lookup
    cb_domain = find_domain_via_clearbit(company_name)
    if cb_domain:
        candidates_domains.append(cb_domain)

    # 2. DuckDuckGo Instant Answer
    ddg_domain = find_domain_via_ddg_instant(company_name)
    if ddg_domain and ddg_domain not in candidates_domains:
        candidates_domains.append(ddg_domain)

    # 3. Clean name heuristic
    clean_heuristic = re.sub(r"[^a-zA-Z0-9]", "", company_name).lower()
    for tld in [".com", ".in", ".ai", ".io", ".co"]:
        test_domain = f"{clean_heuristic}{tld}"
        if test_domain not in candidates_domains and check_mx_valid(test_domain):
            candidates_domains.append(test_domain)
            break

    # 4. Search DDG HTML if still none found
    if not candidates_domains:
        web_domains = find_domains_via_ddg_html(company_name)
        for wd in web_domains:
            if wd not in candidates_domains:
                candidates_domains.append(wd)

    # Build verified email addresses
    verified_emails = []
    for domain in candidates_domains:
        for prefix in GENERIC_PREFIXES[:3]:
            verified_emails.append(f"{prefix}@{domain}")

    return verified_emails
