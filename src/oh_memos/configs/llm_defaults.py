"""
LLM identity defaults — single resolution point for model / endpoint / credential.

Why this module exists
----------------------
Model names, API base URLs and API keys used to be written as literals in a
dozen config builders (``api/config.py``, ``mem_os/utils/default_config.py``,
``configs/llm.py`` ...). Those literals rot: when a hardcoded model reaches
end-of-life upstream the call fails with an opaque HTTP 410 even though ``.env``
already names a valid model, because the literal is what actually reached the
client. See ``docs/CHANGELOG.md`` (2026-09-05) for the incident.

Rule: ``.env`` is the only place that carries a concrete model name, endpoint or
key. Source code asks this module.

Everything is resolved *inside functions*, never at import time — ``load_dotenv()``
runs during application startup, which is after this module is imported, so
module-level constants would freeze pre-dotenv values.
"""

import os


# Neutral fallback endpoint for a fresh checkout with no .env. Deliberately the
# public OpenAI-compatible URL and not any private relay: a private endpoint in
# source is both a leak and a value that silently breaks other machines.
DEFAULT_OPENAI_API_BASE = "https://api.openai.com/v1"


def _env(name: str, default: str = "") -> str:
    """Read an env var, treating whitespace-only as unset."""
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    return value if value else default


# ---------------------------------------------------------------------------
# Primary chat / extraction LLM
# ---------------------------------------------------------------------------


def chat_provider(default: str = "openai") -> str:
    """Backend name for the primary LLM (``MOS_CHAT_MODEL_PROVIDER``)."""
    return _env("MOS_CHAT_MODEL_PROVIDER", default)


MISSING_CHAT_MODEL_HINT = (
    "MOS_CHAT_MODEL is not set. Define it in .env "
    "(the effective file may be src/.env — see docs/CHANGELOG.md 2026-09-05)."
)


def chat_model(default: str = "") -> str:
    """
    Primary model name (``MOS_CHAT_MODEL``).

    Returns ``default`` (empty by default) when unset. This must stay lenient:
    ``api/start_api.py`` evaluates ``DEFAULT_CONFIG =
    APIConfig.get_product_default_config()`` at *module level*, and the Docker
    build's smoke test imports that module with no ``.env`` in the image. Raising
    here would fail the image build rather than the misconfiguration it is meant
    to catch.

    The hard check lives one layer down instead: ``BaseLLMConfig`` rejects an
    empty ``model_name_or_path``, so a real LLM can never be constructed without
    a model name. See :data:`MISSING_CHAT_MODEL_HINT`.
    """
    return _env("MOS_CHAT_MODEL", default)


def require_chat_model() -> str:
    """
    Primary model name, raising when unset.

    Only for call sites that are guaranteed to run *after* dotenv has loaded and
    outside any import chain — never from a config builder reachable at import
    time. Prefer :func:`chat_model` plus the ``BaseLLMConfig`` validator.
    """
    model = chat_model()
    if not model:
        raise ValueError(MISSING_CHAT_MODEL_HINT)
    return model


def chat_api_key(default: str = "") -> str:
    """API key for the primary LLM (``OPENAI_API_KEY``)."""
    return _env("OPENAI_API_KEY", default)


def chat_api_base(default: str = DEFAULT_OPENAI_API_BASE) -> str:
    """API base URL for the primary LLM (``OPENAI_API_BASE``)."""
    return _env("OPENAI_API_BASE", default)


# ---------------------------------------------------------------------------
# MemReader LLM (retrieval-side extraction)
# ---------------------------------------------------------------------------
# Env keys keep the historical ``MEMRADER`` misspelling — renaming them would
# break every deployed .env. Each falls back to the primary LLM setting.


def memreader_model(default: str = "") -> str:
    """MemReader model (``MEMRADER_MODEL``, falling back to ``MOS_CHAT_MODEL``)."""
    return _env("MEMRADER_MODEL", chat_model(default))


def memreader_api_key(default: str = "") -> str:
    """MemReader API key (``MEMRADER_API_KEY``, falling back to ``OPENAI_API_KEY``)."""
    return _env("MEMRADER_API_KEY", chat_api_key(default))


def memreader_api_base(default: str = DEFAULT_OPENAI_API_BASE) -> str:
    """MemReader endpoint (``MEMRADER_API_BASE``, falling back to ``OPENAI_API_BASE``)."""
    return _env("MEMRADER_API_BASE", chat_api_base(default))


def memreader_top_p(default: float = 0.95) -> float | None:
    """MemReader top_p (``MEMRADER_TOP_P``). ``none`` leaves top_p out of the request.

    Some OpenAI-compatible upstreams reject top_p with HTTP 400. Unset or blank
    keeps ``default``.
    """
    value = _env("MEMRADER_TOP_P")
    if not value:
        return default
    if value.lower() in ("none", "null"):
        return None
    return float(value)


# ---------------------------------------------------------------------------
# Fallback LLM (degradation target when the primary times out / is exhausted)
# ---------------------------------------------------------------------------
# No default model on purpose: a literal here would name one specific vendor as
# everyone's backup. Fallback is opt-in via MOS_CHAT_FALLBACK_ENABLED, and
# enabling it without MOS_CHAT_FALLBACK_MODEL should surface as a config error
# rather than a silent call to the wrong provider.


def fallback_backend(default: str = "openai") -> str:
    """Backend for the fallback LLM (``MOS_CHAT_FALLBACK_BACKEND``)."""
    return _env("MOS_CHAT_FALLBACK_BACKEND", default)


def fallback_model(default: str = "") -> str:
    """Fallback model name (``MOS_CHAT_FALLBACK_MODEL``)."""
    return _env("MOS_CHAT_FALLBACK_MODEL", default)


def fallback_api_key(default: str = "") -> str:
    """Fallback API key (``MOS_CHAT_FALLBACK_API_KEY``)."""
    return _env("MOS_CHAT_FALLBACK_API_KEY", default)


def fallback_api_base(default: str = DEFAULT_OPENAI_API_BASE) -> str:
    """Fallback endpoint (``MOS_CHAT_FALLBACK_API_BASE``)."""
    return _env("MOS_CHAT_FALLBACK_API_BASE", default)
