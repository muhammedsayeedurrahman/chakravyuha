"""Chakravyuha configuration — env vars, constants, and settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", str(PROJECT_ROOT / "chromadb"))

# ── API Keys ───────────────────────────────────────────────────────────────
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")

# ── Model Settings ─────────────────────────────────────────────────────────
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
RAG_TOP_K = 5
RAG_SIMILARITY_THRESHOLD = 0.3
RAG_CONFIDENCE_HIGH = 0.7
RAG_CONFIDENCE_LOW = 0.3

# ── LLM Settings ──────────────────────────────────────────────────────────
LLM_ENABLED = os.getenv("LLM_ENABLED", "true").lower() in ("true", "1", "yes")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1024"))
LLM_PRIORITY = os.getenv("LLM_PRIORITY", "mistral,gemini,openrouter,ollama,sarvam")
# Doc generation prefers Ollama (local/private, no content filtering, free)
DOC_GEN_LLM_PRIORITY = os.getenv("DOC_GEN_LLM_PRIORITY", "ollama,mistral,gemini,openrouter,sarvam")

# ── Provider API Keys ────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# ── Provider Model Names ─────────────────────────────────────────────────
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-small-latest")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "qwen/qwen-2.5-72b-instruct:free")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "phi3")
SARVAM_LLM_MODEL = os.getenv("SARVAM_LLM_MODEL", "sarvam-m")

# ── Ollama Settings ──────────────────────────────────────────────────────
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# ── ASR Confidence Tiers ───────────────────────────────────────────────────
ASR_ACCEPT_THRESHOLD = 0.5
ASR_CONFIRM_THRESHOLD = 0.2

# ── Supported Languages ───────────────────────────────────────────────────
SUPPORTED_LANGUAGES = {
    "hi-IN": "Hindi",
    "ta-IN": "Tamil",
    "bn-IN": "Bengali",
    "te-IN": "Telugu",
    "mr-IN": "Marathi",
    "kn-IN": "Kannada",
    "ml-IN": "Malayalam",
    "gu-IN": "Gujarati",
    "od-IN": "Odia",
    "pa-IN": "Punjabi",
    "en-IN": "English",
}

# ── Emergency / Escalation ─────────────────────────────────────────────────
NALSA_HELPLINE = "15100"
POLICE_HELPLINE = "100"
WOMEN_HELPLINE = "181"
CHILD_HELPLINE = "1098"

# ── Legal Disclaimer ──────────────────────────────────────────────────────
DISCLAIMER = (
    "DISCLAIMER: Chakravyuha provides legal INFORMATION, not legal ADVICE. "
    "This tool is for educational and informational purposes only. It does not "
    "constitute legal advice, and no attorney-client relationship is formed. "
    "Always consult a qualified lawyer for legal matters. "
    f"In emergencies, contact Police ({POLICE_HELPLINE}) or NALSA ({NALSA_HELPLINE})."
)

# ── Gradio Settings ────────────────────────────────────────────────────────
GRADIO_PORT = int(os.getenv("GRADIO_PORT", "7860"))
GRADIO_TITLE = "Chakravyuha — AI Legal Assistant for India"


# ── Settings Object ──────────────────────────────────────────────────────

@dataclass(frozen=True)
class Settings:
    """Immutable settings object for dependency injection."""

    # Paths
    project_root: str = str(PROJECT_ROOT)
    data_dir: str = str(DATA_DIR)
    chroma_persist_dir: str = CHROMA_PERSIST_DIR

    # API Keys
    sarvam_api_key: str = SARVAM_API_KEY

    # Model / RAG
    embedding_model: str = EMBEDDING_MODEL
    rag_top_k: int = RAG_TOP_K
    rag_score_threshold: float = RAG_SIMILARITY_THRESHOLD
    rag_confidence_high: float = RAG_CONFIDENCE_HIGH
    rag_confidence_low: float = RAG_CONFIDENCE_LOW

    # LLM
    llm_enabled: bool = LLM_ENABLED
    llm_temperature: float = LLM_TEMPERATURE
    llm_max_tokens: int = LLM_MAX_TOKENS
    llm_priority: str = LLM_PRIORITY
    doc_gen_llm_priority: str = DOC_GEN_LLM_PRIORITY

    # Provider API Keys
    gemini_api_key: str = GEMINI_API_KEY
    mistral_api_key: str = MISTRAL_API_KEY
    openrouter_api_key: str = OPENROUTER_API_KEY

    # Provider Models
    gemini_model: str = GEMINI_MODEL
    mistral_model: str = MISTRAL_MODEL
    openrouter_model: str = OPENROUTER_MODEL
    ollama_model: str = OLLAMA_MODEL
    sarvam_llm_model: str = SARVAM_LLM_MODEL

    # Ollama
    ollama_base_url: str = OLLAMA_BASE_URL

    # ASR
    asr_accept_threshold: float = ASR_ACCEPT_THRESHOLD
    asr_confirm_threshold: float = ASR_CONFIRM_THRESHOLD

    # Helplines
    nalsa_helpline: str = NALSA_HELPLINE
    police_helpline: str = POLICE_HELPLINE
    women_helpline: str = WOMEN_HELPLINE
    child_helpline: str = CHILD_HELPLINE

    # Text
    disclaimer_text: str = DISCLAIMER


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached singleton Settings instance."""
    return Settings()
