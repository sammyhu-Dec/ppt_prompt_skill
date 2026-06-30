import os
from dotenv import load_dotenv

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock").strip().lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
OPENAI_TIMEOUT = float(os.getenv("OPENAI_TIMEOUT", "180").strip())
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output").strip()
DEBUG = os.getenv("DEBUG", "true").strip().lower() in {"1", "true", "yes", "y"}
