"""
MemOS Unified Environment Variable Loader

This module provides a centralized configuration system that:
1. Loads environment variables from .env file
2. Defines all supported configuration options with defaults
3. Performs type conversion and validation
4. Provides a unified interface via get_config()

Usage:
    from memos.configs.env_loader import get_config, EnvConfig

    config = get_config()
    print(config.neo4j_uri)
    print(config.llm_model)
"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


logger = logging.getLogger(__name__)


# =============================================================================
# Environment Variable Definitions
# =============================================================================

# Priority order for .env loading:
# 1. Already set environment variables (system/shell)
# 2. .env file in project root


def _find_project_root() -> Path:
    """Find the project root directory by looking for .env or pyproject.toml."""
    current = Path.cwd()
    for parent in [current] + list(current.parents):
        if (parent / ".env").exists() or (parent / "pyproject.toml").exists():
            return parent
    return current


def _load_env_file() -> None:
    """Load .env file from project root if it exists."""
    project_root = _find_project_root()
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)  # Don't override existing env vars
        logger.debug(f"Loaded .env from {env_path}")
    else:
        load_dotenv()  # Fallback: search from cwd upward


# Load .env on module import
_load_env_file()


# =============================================================================
# Helper Functions
# =============================================================================

def _get_env(key: str, default: str | None = None) -> str | None:
    """Get environment variable, returning None for empty strings."""
    val = os.environ.get(key, "").strip()
    return val if val else default


def _get_env_required(key: str, alternatives: list[str] | None = None) -> str:
    """Get required environment variable, checking alternatives."""
    val = _get_env(key)
    if val:
        return val

    # Check alternative names
    if alternatives:
        for alt in alternatives:
            val = _get_env(alt)
            if val:
                return val

    alt_names = f" (or {', '.join(alternatives)})" if alternatives else ""
    raise ValueError(f"Required environment variable {key}{alt_names} is not set")


def _get_env_bool(key: str, default: bool = False) -> bool:
    """Get environment variable as boolean."""
    val = _get_env(key)
    if val is None:
        return default
    return val.lower() in ("true", "1", "yes", "on")


def _get_env_int(key: str, default: int = 0) -> int:
    """Get environment variable as integer."""
    val = _get_env(key)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        logger.warning(f"Invalid integer value for {key}: {val}, using default {default}")
        return default


def _get_env_float(key: str, default: float = 0.0) -> float:
    """Get environment variable as float."""
    val = _get_env(key)
    if val is None:
        return default
    try:
        return float(val)
    except ValueError:
        logger.warning(f"Invalid float value for {key}: {val}, using default {default}")
        return default


# =============================================================================
# Configuration Dataclass
# =============================================================================

@dataclass
class EnvConfig:
    """
    Unified configuration loaded from environment variables.

    All configuration values are loaded from .env file or environment variables.
    This provides a single source of truth for all configuration.
    """

    # -------------------------------------------------------------------------
    # Base Configuration
    # -------------------------------------------------------------------------
    timezone: str = "Asia/Shanghai"
    cube_path: str = "./data/memos_cubes"
    base_path: str = "."
    enable_default_cube_config: bool = True

    # -------------------------------------------------------------------------
    # MCP Server & API Configuration
    # -------------------------------------------------------------------------
    memos_url: str = "http://localhost:18000"
    memos_user: str = "dev_user"
    memos_default_cube: str = "dev_cube"
    memos_cubes_dir: str = ""

    # MCP Server Timeouts
    timeout_tool: float = 120.0
    timeout_startup: float = 30.0
    timeout_health: float = 5.0
    api_wait_max: float = 60.0
    enable_delete: bool = False
    debug_mode: bool = False

    # -------------------------------------------------------------------------
    # Memory Mode Configuration
    # -------------------------------------------------------------------------
    text_mem_type: str = "tree_text"  # "general_text" or "tree_text"
    enable_reorganize: bool = True
    reorganize_timeout: int = 1800
    reorganize_min_group: int = 10
    async_mode: str = "sync"
    top_k: int = 7

    # -------------------------------------------------------------------------
    # Neo4j Configuration
    # -------------------------------------------------------------------------
    neo4j_backend: str = "neo4j-community"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_http_url: str = "http://localhost:7474/db/neo4j/tx/commit"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""
    neo4j_db_name: str = "neo4j"
    neo4j_shared_db: bool = False

    # -------------------------------------------------------------------------
    # Qdrant Configuration
    # -------------------------------------------------------------------------
    qdrant_host: str | None = "localhost"
    qdrant_port: int | None = 6333
    qdrant_url: str | None = None  # Cloud URL (if set, host/port ignored)
    qdrant_api_key: str | None = None
    qdrant_path: str | None = None  # Local storage path

    # -------------------------------------------------------------------------
    # LLM Configuration
    # -------------------------------------------------------------------------
    llm_provider: str = "openai"
    llm_model: str = ""
    llm_api_key: str = ""
    llm_api_base: str = "https://api.openai.com/v1"
    llm_temperature: float = 0.8
    llm_max_tokens: int = 6000
    llm_top_p: float = 0.9

    # MemReader LLM (retrieval)
    memreader_model: str = ""
    memreader_api_key: str = ""
    memreader_api_base: str = ""
    memreader_max_tokens: int = 6000

    # -------------------------------------------------------------------------
    # Embedder Configuration
    # -------------------------------------------------------------------------
    embedder_backend: str = "universal_api"
    embedder_provider: str = "openai"
    embedder_model: str = "BAAI/bge-m3"
    embedder_api_base: str = ""
    embedder_api_key: str = ""
    embedding_dimension: int = 1024

    # Embedder Fallback Configuration
    embedder_fallback_enabled: bool = False
    embedder_fallback_backend: str = "ollama"
    embedder_fallback_model: str = "nomic-embed-text:latest"
    embedder_fallback_api_base: str = "http://localhost:11434"
    embedder_fallback_embedding_dims: int | None = None
    embedder_fallback_max_retries: int = 3
    embedder_fallback_initial_delay_ms: int = 1000
    embedder_fallback_max_delay_ms: int = 30000
    embedder_fallback_backoff_multiplier: float = 2.0
    embedder_fallback_jitter: bool = True
    embedder_fallback_dimension_strategy: str = "error"

    # -------------------------------------------------------------------------
    # Reranker Configuration
    # -------------------------------------------------------------------------
    reranker_backend: str = "http_bge"
    reranker_url: str = ""
    reranker_model: str = "netease-youdao/bce-reranker-base_v1"
    reranker_api_key: str = ""
    reranker_headers_extra: str = ""
    reranker_strategy: str = "single_turn"

    # -------------------------------------------------------------------------
    # Optional Services
    # -------------------------------------------------------------------------
    # Internet Search
    enable_internet: bool = False
    bocha_api_key: str = ""
    search_mode: str = "fast"
    fine_strategy: str = "rewrite"

    # Preference Memory
    enable_preference_memory: bool = True
    preference_adder_mode: str = "fast"
    dedup_pref_exp_by_textual: bool = False

    # MemReader Chunking
    mem_reader_backend: str = "simple_struct"
    mem_reader_chunk_type: str = "default"
    mem_reader_chunk_token_size: int = 1600
    mem_reader_chunk_sess_size: int = 10
    mem_reader_chunk_overlap: int = 2

    # Scheduler
    enable_scheduler: bool = False
    scheduler_top_k: int = 10
    scheduler_act_mem_update_interval: int = 300
    scheduler_context_window_size: int = 5

    # Milvus (optional)
    milvus_uri: str = "http://localhost:19530"
    milvus_user: str = "root"
    milvus_password: str = ""

    # Redis (optional)
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""

    def __post_init__(self):
        """Validate configuration after initialization."""
        # Ensure cubes_dir is set
        if not self.memos_cubes_dir:
            self.memos_cubes_dir = str(Path(self.cube_path).absolute())


def _load_config_from_env() -> EnvConfig:
    """Load configuration from environment variables."""
    return EnvConfig(
        # Base
        timezone=_get_env("TZ", "Asia/Shanghai"),
        cube_path=_get_env("MOS_CUBE_PATH", "./data/memos_cubes"),
        base_path=_get_env("MEMOS_BASE_PATH", "."),
        enable_default_cube_config=_get_env_bool("MOS_ENABLE_DEFAULT_CUBE_CONFIG", True),

        # MCP Server & API
        memos_url=_get_env("MEMOS_URL") or _get_env("MEMOS_BASE_URL", "http://localhost:18000"),
        memos_user=_get_env("MEMOS_USER") or _get_env("MOS_USER_ID", "dev_user"),
        memos_default_cube=_get_env("MEMOS_DEFAULT_CUBE", "dev_cube"),
        memos_cubes_dir=_get_env("MEMOS_CUBES_DIR", ""),

        # Timeouts
        timeout_tool=_get_env_float("MEMOS_TIMEOUT_TOOL", 120.0),
        timeout_startup=_get_env_float("MEMOS_TIMEOUT_STARTUP", 30.0),
        timeout_health=_get_env_float("MEMOS_TIMEOUT_HEALTH", 5.0),
        api_wait_max=_get_env_float("MEMOS_API_WAIT_MAX", 60.0),
        enable_delete=_get_env_bool("MEMOS_ENABLE_DELETE", False),
        debug_mode=_get_env_bool("MEMOS_DEBUG", False),

        # Memory Mode
        text_mem_type=_get_env("MOS_TEXT_MEM_TYPE", "tree_text"),
        enable_reorganize=_get_env_bool("MOS_ENABLE_REORGANIZE", True),
        reorganize_timeout=_get_env_int("MOS_REORGANIZE_TIMEOUT", 1800),
        reorganize_min_group=_get_env_int("MOS_REORGANIZE_MIN_GROUP", 10),
        async_mode=_get_env("ASYNC_MODE", "sync"),
        top_k=_get_env_int("MOS_TOP_K", 7),

        # Neo4j
        neo4j_backend=_get_env("NEO4J_BACKEND", "neo4j-community"),
        neo4j_uri=_get_env("NEO4J_URI", "bolt://localhost:7687"),
        neo4j_http_url=_get_env("NEO4J_HTTP_URL", "http://localhost:7474/db/neo4j/tx/commit"),
        neo4j_user=_get_env("NEO4J_USER", "neo4j"),
        neo4j_password=_get_env("NEO4J_PASSWORD", ""),
        neo4j_db_name=_get_env("NEO4J_DB_NAME", "neo4j"),
        neo4j_shared_db=_get_env_bool("MOS_NEO4J_SHARED_DB", False),

        # Qdrant
        qdrant_host=_get_env("QDRANT_HOST", "localhost"),
        qdrant_port=_get_env_int("QDRANT_PORT", 6333) if _get_env("QDRANT_PORT") else 6333,
        qdrant_url=_get_env("QDRANT_URL"),
        qdrant_api_key=_get_env("QDRANT_API_KEY"),
        qdrant_path=_get_env("QDRANT_PATH"),

        # LLM
        llm_provider=_get_env("MOS_CHAT_MODEL_PROVIDER", "openai"),
        llm_model=_get_env("MOS_CHAT_MODEL", ""),
        llm_api_key=_get_env("OPENAI_API_KEY", ""),
        llm_api_base=_get_env("OPENAI_API_BASE", "https://api.openai.com/v1"),
        llm_temperature=_get_env_float("MOS_CHAT_TEMPERATURE", 0.8),
        llm_max_tokens=_get_env_int("MOS_MAX_TOKENS", 6000),
        llm_top_p=_get_env_float("MOS_TOP_P", 0.9),

        # MemReader LLM
        memreader_model=_get_env("MEMRADER_MODEL", ""),
        memreader_api_key=_get_env("MEMRADER_API_KEY", ""),
        memreader_api_base=_get_env("MEMRADER_API_BASE", ""),
        memreader_max_tokens=_get_env_int("MEMRADER_MAX_TOKENS", 6000),

        # Embedder
        embedder_backend=_get_env("MOS_EMBEDDER_BACKEND", "universal_api"),
        embedder_provider=_get_env("MOS_EMBEDDER_PROVIDER", "openai"),
        embedder_model=_get_env("MOS_EMBEDDER_MODEL", "BAAI/bge-m3"),
        embedder_api_base=_get_env("MOS_EMBEDDER_API_BASE", ""),
        embedder_api_key=_get_env("MOS_EMBEDDER_API_KEY", ""),
        embedding_dimension=_get_env_int("EMBEDDING_DIMENSION", 1024),

        # Embedder Fallback
        embedder_fallback_enabled=_get_env_bool("MOS_EMBEDDER_FALLBACK_ENABLED", False),
        embedder_fallback_backend=_get_env("MOS_EMBEDDER_FALLBACK_BACKEND", "ollama"),
        embedder_fallback_model=_get_env("MOS_EMBEDDER_FALLBACK_MODEL", "nomic-embed-text:latest"),
        embedder_fallback_api_base=_get_env("MOS_EMBEDDER_FALLBACK_API_BASE", "http://localhost:11434"),
        embedder_fallback_embedding_dims=_get_env_int("MOS_EMBEDDER_FALLBACK_EMBEDDING_DIMS", 0) or None,
        embedder_fallback_max_retries=_get_env_int("MOS_EMBEDDER_FALLBACK_MAX_RETRIES", 3),
        embedder_fallback_initial_delay_ms=_get_env_int("MOS_EMBEDDER_FALLBACK_INITIAL_DELAY_MS", 1000),
        embedder_fallback_max_delay_ms=_get_env_int("MOS_EMBEDDER_FALLBACK_MAX_DELAY_MS", 30000),
        embedder_fallback_backoff_multiplier=_get_env_float("MOS_EMBEDDER_FALLBACK_BACKOFF_MULTIPLIER", 2.0),
        embedder_fallback_jitter=_get_env_bool("MOS_EMBEDDER_FALLBACK_JITTER", True),
        embedder_fallback_dimension_strategy=_get_env("MOS_EMBEDDER_FALLBACK_DIMENSION_STRATEGY", "error"),

        # Reranker
        reranker_backend=_get_env("MOS_RERANKER_BACKEND", "http_bge"),
        reranker_url=_get_env("MOS_RERANKER_URL", ""),
        reranker_model=_get_env("MOS_RERANKER_MODEL", "netease-youdao/bce-reranker-base_v1"),
        reranker_api_key=_get_env("MOS_RERANKER_API_KEY", ""),
        reranker_headers_extra=_get_env("MOS_RERANKER_HEADERS_EXTRA", ""),
        reranker_strategy=_get_env("MOS_RERANKER_STRATEGY", "single_turn"),

        # Internet Search
        enable_internet=_get_env_bool("ENABLE_INTERNET", False),
        bocha_api_key=_get_env("BOCHA_API_KEY", ""),
        search_mode=_get_env("SEARCH_MODE", "fast"),
        fine_strategy=_get_env("FINE_STRATEGY", "rewrite"),

        # Preference Memory
        enable_preference_memory=_get_env_bool("ENABLE_PREFERENCE_MEMORY", True),
        preference_adder_mode=_get_env("PREFERENCE_ADDER_MODE", "fast"),
        dedup_pref_exp_by_textual=_get_env_bool("DEDUP_PREF_EXP_BY_TEXTUAL", False),

        # MemReader Chunking
        mem_reader_backend=_get_env("MEM_READER_BACKEND", "simple_struct"),
        mem_reader_chunk_type=_get_env("MEM_READER_CHAT_CHUNK_TYPE", "default"),
        mem_reader_chunk_token_size=_get_env_int("MEM_READER_CHAT_CHUNK_TOKEN_SIZE", 1600),
        mem_reader_chunk_sess_size=_get_env_int("MEM_READER_CHAT_CHUNK_SESS_SIZE", 10),
        mem_reader_chunk_overlap=_get_env_int("MEM_READER_CHAT_CHUNK_OVERLAP", 2),

        # Scheduler
        enable_scheduler=_get_env_bool("MOS_ENABLE_SCHEDULER", False),
        scheduler_top_k=_get_env_int("MOS_SCHEDULER_TOP_K", 10),
        scheduler_act_mem_update_interval=_get_env_int("MOS_SCHEDULER_ACT_MEM_UPDATE_INTERVAL", 300),
        scheduler_context_window_size=_get_env_int("MOS_SCHEDULER_CONTEXT_WINDOW_SIZE", 5),

        # Milvus
        milvus_uri=_get_env("MILVUS_URI", "http://localhost:19530"),
        milvus_user=_get_env("MILVUS_USER_NAME", "root"),
        milvus_password=_get_env("MILVUS_PASSWORD", ""),

        # Redis
        redis_host=_get_env("MEMSCHEDULER_REDIS_HOST", "localhost"),
        redis_port=_get_env_int("MEMSCHEDULER_REDIS_PORT", 6379),
        redis_db=_get_env_int("MEMSCHEDULER_REDIS_DB", 0),
        redis_password=_get_env("MEMSCHEDULER_REDIS_PASSWORD", ""),
    )


# =============================================================================
# Singleton Configuration Instance
# =============================================================================

_config_instance: EnvConfig | None = None


def get_config(reload: bool = False) -> EnvConfig:
    """
    Get the singleton configuration instance.

    Args:
        reload: If True, reload configuration from environment.

    Returns:
        EnvConfig: The configuration instance.
    """
    global _config_instance
    if _config_instance is None or reload:
        _config_instance = _load_config_from_env()
        logger.info("Configuration loaded from environment")
    return _config_instance


def reload_config() -> EnvConfig:
    """Reload configuration from environment variables."""
    _load_env_file()
    return get_config(reload=True)


# =============================================================================
# Convenience Functions for Common Access Patterns
# =============================================================================

def get_neo4j_config() -> dict[str, Any]:
    """Get Neo4j configuration as a dictionary."""
    cfg = get_config()
    return {
        "backend": cfg.neo4j_backend,
        "uri": cfg.neo4j_uri,
        "user": cfg.neo4j_user,
        "password": cfg.neo4j_password,
        "db_name": cfg.neo4j_db_name,
        "http_url": cfg.neo4j_http_url,
    }


def get_qdrant_config() -> dict[str, Any]:
    """Get Qdrant configuration as a dictionary."""
    cfg = get_config()
    config = {}

    if cfg.qdrant_url:
        # Cloud mode
        config["url"] = cfg.qdrant_url
        if cfg.qdrant_api_key:
            config["api_key"] = cfg.qdrant_api_key
    else:
        # Local mode
        if cfg.qdrant_host:
            config["host"] = cfg.qdrant_host
        if cfg.qdrant_port:
            config["port"] = cfg.qdrant_port
        if cfg.qdrant_path:
            config["path"] = cfg.qdrant_path

    return config


def get_llm_config() -> dict[str, Any]:
    """Get LLM configuration as a dictionary."""
    cfg = get_config()
    return {
        "backend": cfg.llm_provider,
        "model_name_or_path": cfg.llm_model,
        "api_key": cfg.llm_api_key,
        "api_base": cfg.llm_api_base,
        "temperature": cfg.llm_temperature,
        "max_tokens": cfg.llm_max_tokens,
        "top_p": cfg.llm_top_p,
    }


def get_embedder_config() -> dict[str, Any]:
    """Get embedder configuration as a dictionary."""
    cfg = get_config()
    return {
        "backend": cfg.embedder_backend,
        "provider": cfg.embedder_provider,
        "model_name_or_path": cfg.embedder_model,
        "base_url": cfg.embedder_api_base,
        "api_key": cfg.embedder_api_key,
        "embedding_dims": cfg.embedding_dimension,
    }


def get_embedder_fallback_config() -> dict[str, Any]:
    """Get embedder fallback configuration as a dictionary."""
    cfg = get_config()
    return {
        "enabled": cfg.embedder_fallback_enabled,
        "fallback_backend": cfg.embedder_fallback_backend,
        "fallback_model": cfg.embedder_fallback_model,
        "fallback_api_base": cfg.embedder_fallback_api_base,
        "fallback_embedding_dims": cfg.embedder_fallback_embedding_dims,
        "max_retries": cfg.embedder_fallback_max_retries,
        "initial_delay_ms": cfg.embedder_fallback_initial_delay_ms,
        "max_delay_ms": cfg.embedder_fallback_max_delay_ms,
        "backoff_multiplier": cfg.embedder_fallback_backoff_multiplier,
        "jitter": cfg.embedder_fallback_jitter,
        "dimension_mismatch_strategy": cfg.embedder_fallback_dimension_strategy,
    }


def get_reranker_config() -> dict[str, Any]:
    """Get reranker configuration as a dictionary."""
    cfg = get_config()
    return {
        "backend": cfg.reranker_backend,
        "url": cfg.reranker_url,
        "model": cfg.reranker_model,
        "api_key": cfg.reranker_api_key,
        "headers_extra": cfg.reranker_headers_extra,
        "strategy": cfg.reranker_strategy,
    }


# =============================================================================
# Validation Functions
# =============================================================================

def validate_required_config() -> list[str]:
    """
    Validate that all required configuration values are set.

    Returns:
        List of missing required configuration keys.
    """
    cfg = get_config()
    missing = []

    # Check required values
    if not cfg.memos_url:
        missing.append("MEMOS_URL")
    if not cfg.memos_user:
        missing.append("MEMOS_USER")
    if not cfg.memos_default_cube:
        missing.append("MEMOS_DEFAULT_CUBE")

    # For tree_text mode, check additional requirements
    if cfg.text_mem_type == "tree_text":
        if not cfg.neo4j_password:
            missing.append("NEO4J_PASSWORD")
        if not cfg.llm_api_key:
            missing.append("OPENAI_API_KEY (or LLM API key)")
        if not cfg.embedder_api_key:
            missing.append("MOS_EMBEDDER_API_KEY")

    return missing


def print_config_summary() -> None:
    """Print a summary of the current configuration (for debugging)."""
    cfg = get_config()
    print("=" * 60)
    print("MemOS Configuration Summary")
    print("=" * 60)
    print(f"  Mode: {cfg.text_mem_type}")
    print(f"  User: {cfg.memos_user}")
    print(f"  Cube: {cfg.memos_default_cube}")
    print(f"  API:  {cfg.memos_url}")
    print("-" * 60)
    print(f"  Neo4j: {cfg.neo4j_uri}")
    print(f"  Qdrant: {cfg.qdrant_host}:{cfg.qdrant_port}" if cfg.qdrant_host else f"  Qdrant: {cfg.qdrant_url}")
    print(f"  LLM: {cfg.llm_provider}/{cfg.llm_model}")
    print(f"  Embedder: {cfg.embedder_provider}/{cfg.embedder_model}")
    print("=" * 60)
