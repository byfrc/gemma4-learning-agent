from __future__ import annotations

import os
from pathlib import Path
from functools import lru_cache

from dotenv import load_dotenv

from .subjects import DEFAULT_SUBJECT, normalize_subject

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")


class Settings:
    app_name = os.getenv("APP_NAME", "Gemma4 Private Learning Agent API")
    api_host = os.getenv("API_HOST", "0.0.0.0")
    api_port = int(os.getenv("API_PORT", "8000"))
    cors_origins = [x.strip() for x in os.getenv(
        "CORS_ORIGINS", "http://localhost:8080,http://127.0.0.1:8080"
    ).split(",") if x.strip()]

    model_provider = os.getenv("MODEL_PROVIDER", "openai_compatible").lower()
    vllm_base_url = os.getenv("VLLM_BASE_URL", "http://127.0.0.1:8001/v1").rstrip("/")
    vllm_api_key = os.getenv("VLLM_API_KEY", "EMPTY")
    vllm_model = os.getenv("VLLM_MODEL", "google/gemma4-learning")

    auth_username = os.getenv("AUTH_USERNAME", "admin")
    auth_password = os.getenv("AUTH_PASSWORD", "admin123")
    auth_secret_key = os.getenv(
        "AUTH_SECRET_KEY",
        "gemma4-learning-agent-local-secret-change-me",
    )
    session_ttl_hours = int(os.getenv("SESSION_TTL_HOURS", "12"))

    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    ollama_model = os.getenv("OLLAMA_MODEL", "gemma4:e4b")

    rag_top_k_default = int(os.getenv("RAG_TOP_K_DEFAULT", "3"))
    rag_chunk_size = int(os.getenv("RAG_CHUNK_SIZE", "500"))
    rag_chunk_overlap = int(os.getenv("RAG_CHUNK_OVERLAP", "90"))
    max_upload_mb = int(os.getenv("MAX_UPLOAD_MB", "30"))
    document_ocr_enabled = os.getenv("DOCUMENT_OCR_ENABLED", "auto").lower()
    document_ocr_lang = os.getenv("DOCUMENT_OCR_LANG", "ch")
    document_ocr_device = os.getenv("DOCUMENT_OCR_DEVICE", "cpu")
    office_converter = os.getenv("OFFICE_CONVERTER", "soffice")
    office_converter_timeout = int(os.getenv("OFFICE_CONVERTER_TIMEOUT", "120"))
    default_subject = normalize_subject(
        os.getenv("DEFAULT_SUBJECT", DEFAULT_SUBJECT)
    )

    knowledge_dir = Path(os.getenv("KNOWLEDGE_DIR", str(BACKEND_DIR / "data" / "knowledge")))
    rag_index_path = Path(os.getenv("RAG_INDEX_PATH", str(BACKEND_DIR / "data" / "hybrid_rag.joblib")))
    chat_log_path = Path(os.getenv("CHAT_LOG_PATH", str(BACKEND_DIR / "data" / "qa_history.jsonl")))
    feedback_log_path = Path(os.getenv("FEEDBACK_LOG_PATH", str(BACKEND_DIR / "data" / "feedback.jsonl")))
    subject_base_dir = Path(
        os.getenv(
            "SUBJECT_BASE_DIR",
            str(BACKEND_DIR / "data" / "subjects"),
        )
    )
    conversation_db_path = Path(
        os.getenv(
            "CONVERSATION_DB_PATH",
            str(BACKEND_DIR / "data" / "learning_agent.db"),
        )
    )

    def subject_key(self, subject: str | None = None) -> str:
        if subject is None:
            return self.default_subject
        return normalize_subject(subject)

    def knowledge_dir_for(self, subject: str | None = None) -> Path:
        key = self.subject_key(subject)
        if key == self.default_subject:
            path = self.knowledge_dir
        else:
            path = self.subject_base_dir / key / "knowledge"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def rag_index_path_for(self, subject: str | None = None) -> Path:
        key = self.subject_key(subject)
        if key == self.default_subject:
            path = self.rag_index_path
        else:
            path = self.subject_base_dir / key / "hybrid_rag.joblib"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def chat_log_path_for(self, subject: str | None = None) -> Path:
        key = self.subject_key(subject)
        if key == self.default_subject:
            path = self.chat_log_path
        else:
            path = self.subject_base_dir / key / "qa_history.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def feedback_log_path_for(self, subject: str | None = None) -> Path:
        key = self.subject_key(subject)
        if key == self.default_subject:
            path = self.feedback_log_path
        else:
            path = self.subject_base_dir / key / "feedback.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.knowledge_dir.mkdir(parents=True, exist_ok=True)
    settings.rag_index_path.parent.mkdir(parents=True, exist_ok=True)
    settings.chat_log_path.parent.mkdir(parents=True, exist_ok=True)
    settings.feedback_log_path.parent.mkdir(parents=True, exist_ok=True)
    settings.conversation_db_path.parent.mkdir(parents=True, exist_ok=True)
    settings.subject_base_dir.mkdir(parents=True, exist_ok=True)
    return settings
