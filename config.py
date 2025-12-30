import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "brain.db"
FINDINGS_PATH = BASE_DIR / "findings.json"

# Telegram
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "")
TG_CHAT_ID = os.getenv("TG_CHAT_ID", "1198523752")

# AI API
API_KEY = os.getenv("API_KEY", "")
API_URL = os.getenv("API_URL", "https://openrouter.ai/api/v1/chat/completions")
MODEL = os.getenv("MODEL", "deepseek/deepseek-chat")

# GitHub
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_USER = os.getenv("GITHUB_USER", "djontrevor4")

# MOEX Tickers
TICKERS = [
    "SBER", "GAZP", "LKOH", "ROSN", "NVTK",
    "GMKN", "YNDX", "MTSS", "MGNT", "POLY",
    "CHMF", "NLMK", "ALRS", "MOEX", "TATN",
    "SNGS", "VTBR", "PHOR", "RUAL", "PLZL",
    "AFLT", "PIKK", "IRAO", "FEES", "HYDR",
    "SFIN", "MTLR", "SMLT", "OZON", "TCSG"
]
