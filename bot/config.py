import os
import shutil
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Candidate Info
CANDIDATE_NAME = os.getenv("CANDIDATE_NAME", "Mahansh Gaur")
CANDIDATE_PHONE = os.getenv("CANDIDATE_PHONE", "+917073320270")
CANDIDATE_LINKEDIN = os.getenv("CANDIDATE_LINKEDIN", "https://www.linkedin.com/in/mahansh-gaur-4306751b3/")
CANDIDATE_GITHUB = os.getenv("CANDIDATE_GITHUB", "https://github.com/mahanshstarktech")

# Credentials
GMAIL_USER = os.getenv("GMAIL_USER", "mahanshgaur@gmail.com")
GMAIL_APP_PASS = os.getenv("GMAIL_APP_PASS", "").replace(" ", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Scraper CLI Paths
LINKEDIN_CLI = BASE_DIR / "scrapers/linkedin/src/cli.ts"
FREEHIRE_CLI = BASE_DIR / "scrapers/freehire/src/cli.ts"

# Compiler
LUALATEX_CUSTOM = Path.home() / "Library/TinyTeX/bin/universal-darwin/lualatex"
if LUALATEX_CUSTOM.exists():
    LUALATEX_PATH = str(LUALATEX_CUSTOM)
else:
    LUALATEX_PATH = shutil.which("lualatex") or "lualatex"

# Safety Throttles & Cold Email Policy
MAX_EMAILS_PER_DAY = int(os.getenv("MAX_EMAILS_PER_DAY", "15"))
MAX_EMAILS_PER_DOMAIN_PER_WEEK = int(os.getenv("MAX_EMAILS_PER_DOMAIN_PER_WEEK", "2"))
MIN_DELAY_BETWEEN_EMAILS_SECONDS = int(os.getenv("MIN_DELAY_BETWEEN_EMAILS_SECONDS", "15"))
MIN_MATCH_SCORE = int(os.getenv("MIN_MATCH_SCORE", "65"))

