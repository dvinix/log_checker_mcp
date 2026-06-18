import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_OWNER = os.getenv("GITHUB_OWNER", "dvinix")
GITHUB_REPO = os.getenv("GITHUB_REPO", "SecondBrain")
GITHUB_BASE_BRANCH = os.getenv("GITHUB_BASE_BRANCH", "main")

HF_SPACE_ID = os.getenv("HF_SPACE_ID", "dvinix/secondbrain")
CRON_SCHEDULE = os.getenv("CRON_SCHEDULE", "*/5 * * * *")
SOURCE_DIR = os.getenv("SOURCE_DIR", "../")
ALLOWED_EXTENSIONS = os.getenv("ALLOWED_EXTENSIONS", ".py,.js,.ts,.tsx").split(",")
ERROR_DEDUP_TTL_MS = int(os.getenv("ERROR_DEDUP_TTL_MS", "3600000"))
