import os
from pathlib import Path

APP_NAME = "PrepPilot"
DATA_ROOT = Path(".exam_helper_data")
MODULES_DIR = DATA_ROOT / "modules"


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200
DEFAULT_RETRIEVAL_K = 8
DEFAULT_MAX_RETRIES = _env_int("MAX_RETRIES", 1)
DEFAULT_QUIZ_DIFFICULTY = "Medium"
DEFAULT_STUDY_HOURS_PER_DAY = 2
LARGE_CHUNK_THRESHOLD = 1200
DEFAULT_TIMEOUT_SECONDS = _env_float("LLM_TIMEOUT_SECONDS", 30.0)
DEFAULT_GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

PRIMARY_MODEL = os.getenv("PRIMARY_MODEL", "llama-3.1-8b-instant")
FALLBACK_MODEL_1 = os.getenv("FALLBACK_MODEL_1", "openai/gpt-oss-20b")

DEFAULT_QUIZ_MODEL = PRIMARY_MODEL
DEFAULT_PLAN_MODEL = FALLBACK_MODEL_1

QUIZ_MODEL_FALLBACK = [
    FALLBACK_MODEL_1,
]

PLAN_MODEL_FALLBACK = [
    PRIMARY_MODEL,
]

SUPPORTED_EXTENSIONS = {".pdf", ".pptx"}
CACHE_SCHEMA_VERSION = "v5_readability_detailed_outputs"


def ensure_data_dirs() -> None:
    MODULES_DIR.mkdir(parents=True, exist_ok=True)


def module_dir(module_id: str) -> Path:
    return MODULES_DIR / module_id


def module_manifest_path(module_id: str) -> Path:
    return module_dir(module_id) / "manifest.json"


def module_chunks_path(module_id: str) -> Path:
    return module_dir(module_id) / "chunks.json"


def module_quiz_cache_path(module_id: str) -> Path:
    return module_dir(module_id) / "quiz_cache.json"


def module_plan_cache_path(module_id: str) -> Path:
    return module_dir(module_id) / "plan_cache.json"


def module_topic_index_path(module_id: str) -> Path:
    return module_dir(module_id) / "topic_index.joblib"


def module_vectorstore_dir(module_id: str) -> Path:
    return module_dir(module_id) / "vectorstore"


def module_relevance_labels_path(module_id: str) -> Path:
    return module_dir(module_id) / "relevance_labels.json"


def module_relevance_overrides_path(module_id: str) -> Path:
    return module_dir(module_id) / "relevance_overrides.json"
