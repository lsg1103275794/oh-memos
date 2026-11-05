from typing import Any, ClassVar

from pydantic import Field, SerializeAsAny, field_validator, model_validator

from oh_memos.configs import llm_defaults
from oh_memos.configs.base import BaseConfig


class BaseLLMConfig(BaseConfig):
    """Base configuration class for LLMs."""

    model_name_or_path: str = Field(..., description="Model name or path")
    temperature: float = Field(default=0.7, description="Temperature for sampling")
    max_tokens: int = Field(default=8192, description="Maximum number of tokens to generate")
    top_p: float = Field(default=0.95, description="Top-p sampling parameter")
    top_k: int = Field(default=50, description="Top-k sampling parameter")
    remove_think_prefix: bool = Field(
        default=False,
        description="Remove content within think tags from the generated text",
    )
    default_headers: dict[str, Any] | None = Field(
        default=None, description="Default headers for LLM requests"
    )

    @field_validator("model_name_or_path")
    @classmethod
    def reject_blank_model(cls, value: str) -> str:
        """
        Reject a blank model name.

        This is where the missing-model check belongs. The config *builders* stay
        lenient because ``api/start_api.py`` evaluates ``DEFAULT_CONFIG`` at module
        level and the Docker build imports it with no ``.env`` present — raising
        there fails the image build instead of the misconfiguration. By the time an
        LLM config is actually constructed, dotenv has run, so a blank name here
        really does mean the variable is unset.

        Without this, ``model_name_or_path=""`` validates fine and only surfaces as
        an opaque upstream error on the first call.
        """
        if not value or not value.strip():
            raise ValueError(llm_defaults.MISSING_CHAT_MODEL_HINT)
        return value


class OpenAILLMConfig(BaseLLMConfig):
    api_key: str = Field(..., description="API key for OpenAI")
    # default_factory, not a literal: OPENAI_API_BASE must be read when the config
    # is instantiated (post-dotenv), not when this module is imported.
    api_base: str = Field(
        default_factory=llm_defaults.chat_api_base,
        description="Base URL for OpenAI-compatible API (env: OPENAI_API_BASE)",
    )
    extra_body: Any = Field(default=None, description="extra body")
    # None leaves top_p out of the request, for upstreams that reject it (HTTP 400).
    top_p: float | None = Field(default=0.95, description="Top-p sampling parameter")


class OpenAIResponsesLLMConfig(BaseLLMConfig):
    api_key: str = Field(..., description="API key for OpenAI")
    api_base: str = Field(
        default_factory=llm_defaults.chat_api_base,
        description="Base URL for OpenAI responses API (env: OPENAI_API_BASE)",
    )
    extra_body: Any = Field(default=None, description="extra body")
    enable_thinking: bool = Field(
        default=False,
        description="Enable reasoning outputs from vLLM",
    )


class QwenLLMConfig(BaseLLMConfig):
    api_key: str = Field(..., description="API key for DashScope (Qwen)")
    api_base: str = Field(
        default="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        description="Base URL for Qwen OpenAI-compatible API",
    )
    extra_body: Any = Field(default=None, description="extra body")


class DeepSeekLLMConfig(BaseLLMConfig):
    api_key: str = Field(..., description="API key for DeepSeek")
    api_base: str = Field(
        default="https://api.deepseek.com",
        description="Base URL for DeepSeek OpenAI-compatible API",
    )
    extra_body: Any = Field(default=None, description="Extra options for API")


class AzureLLMConfig(BaseLLMConfig):
    base_url: str = Field(
        default="https://api.openai.azure.com/",
        description="Base URL for Azure OpenAI API",
    )
    api_version: str = Field(
        default="2024-03-01-preview",
        description="API version for Azure OpenAI",
    )
    api_key: str = Field(..., description="API key for Azure OpenAI")


class AzureResponsesLLMConfig(BaseLLMConfig):
    base_url: str = Field(
        default="https://api.openai.azure.com/",
        description="Base URL for Azure OpenAI API",
    )
    api_version: str = Field(
        default="2024-03-01-preview",
        description="API version for Azure OpenAI",
    )
    api_key: str = Field(..., description="API key for Azure OpenAI")


class OllamaLLMConfig(BaseLLMConfig):
    api_base: str = Field(
        default="http://localhost:11434",
        description="Base URL for Ollama API",
    )
    enable_thinking: bool = Field(
        default=False,
        description="Enable reasoning outputs from Ollama",
    )


class HFLLMConfig(BaseLLMConfig):
    do_sample: bool = Field(
        default=False,
        description="Whether to use sampling (if False, always greedy/argmax decoding)",
    )
    add_generation_prompt: bool = Field(
        default=True,
        description="Apply generation template for the conversation",
    )


class VLLMLLMConfig(BaseLLMConfig):
    api_key: str = Field(default="", description="API key for vLLM (optional for local server)")
    api_base: str = Field(
        default="http://localhost:8088/v1",
        description="Base URL for vLLM API",
    )
    enable_thinking: bool = Field(
        default=False,
        description="Enable reasoning outputs from vLLM",
    )


class LLMFallbackConfig(BaseConfig):
    """Configuration for LLM fallback behavior.

    Mirrors ``oh_memos.configs.embedder.FallbackConfig`` but targets chat/completion
    LLMs. When the primary LLM is unavailable (timeout / quota exhausted / repeated
    transient failure), calls are automatically degraded to a backup LLM.
    """

    enabled: bool = Field(default=False, description="Enable automatic fallback to backup LLM")
    fallback_backend: str = Field(
        default="openai", description="Backend to use for fallback (e.g., 'openai')"
    )
    # No literal model / endpoint default: naming one vendor as everyone's backup is
    # what rots. Both come from .env (MOS_CHAT_FALLBACK_MODEL / _API_BASE).
    fallback_model: str = Field(
        default_factory=llm_defaults.fallback_model,
        description="Model name for fallback LLM (env: MOS_CHAT_FALLBACK_MODEL)",
    )
    fallback_api_key: str = Field(default="", description="API key for fallback LLM")
    fallback_api_base: str = Field(
        default_factory=llm_defaults.fallback_api_base,
        description="API base URL for fallback LLM (env: MOS_CHAT_FALLBACK_API_BASE)",
    )
    fallback_temperature: float = Field(
        default=0.6, description="Sampling temperature for fallback LLM"
    )
    fallback_max_tokens: int = Field(
        default=6000, description="Maximum tokens to generate for fallback LLM"
    )
    primary_timeout: float = Field(
        default=60.0,
        ge=1.0,
        le=600.0,
        description="Max seconds a single primary-LLM attempt may take before failing over to the backup",
    )
    max_retries: int = Field(
        default=3, ge=1, le=10, description="Maximum retry attempts for transient errors"
    )
    initial_delay_ms: int = Field(
        default=1000, ge=100, le=60000, description="Initial retry delay in milliseconds"
    )
    max_delay_ms: int = Field(
        default=30000, ge=1000, le=300000, description="Maximum retry delay in milliseconds"
    )
    backoff_multiplier: float = Field(
        default=2.0, ge=1.0, le=5.0, description="Exponential backoff multiplier"
    )
    jitter: bool = Field(default=True, description="Add random jitter to retry delays")

    @model_validator(mode="after")
    def validate_fallback_target(self) -> "LLMFallbackConfig":
        """
        Reject an enabled-but-unconfigured fallback.

        Without this, an empty ``fallback_model`` builds a valid-looking config and
        only surfaces when the primary already failed and the backup call returns a
        confusing upstream error — the worst moment to discover a config gap.
        """
        if self.enabled and not self.fallback_model:
            raise ValueError(
                "MOS_CHAT_FALLBACK_ENABLED is true but MOS_CHAT_FALLBACK_MODEL is not set."
            )
        return self


class LLMConfigFactory(BaseConfig):
    """Factory class for creating LLM configurations."""

    backend: str = Field(..., description="Backend for LLM")
    config: dict[str, Any] | SerializeAsAny[BaseLLMConfig] = Field(..., description="Configuration for the LLM backend")

    backend_to_class: ClassVar[dict[str, Any]] = {
        "openai": OpenAILLMConfig,
        "ollama": OllamaLLMConfig,
        "azure": AzureLLMConfig,
        "huggingface": HFLLMConfig,
        "vllm": VLLMLLMConfig,
        "huggingface_singleton": HFLLMConfig,  # Add singleton support
        "qwen": QwenLLMConfig,
        "deepseek": DeepSeekLLMConfig,
        "openai_new": OpenAIResponsesLLMConfig,
    }

    @field_validator("backend")
    @classmethod
    def validate_backend(cls, backend: str) -> str:
        """Validate the backend field."""
        if backend not in cls.backend_to_class:
            raise ValueError(f"Invalid backend: {backend}")
        return backend

    @model_validator(mode="after")
    def create_config(self) -> "LLMConfigFactory":
        config_class = self.backend_to_class[self.backend]
        if isinstance(self.config, dict):
            self.config = config_class(**self.config)
        return self

