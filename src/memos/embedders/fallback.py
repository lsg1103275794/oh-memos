"""
Fallback Embedder with automatic retry and degradation support.

This module provides a wrapper embedder that automatically falls back to a
backup embedder when the primary embedder fails. It includes:
- Intelligent error classification (transient vs permanent)
- Exponential backoff retry for transient errors
- Automatic fallback to backup embedder
- Embedding dimension mismatch handling
"""

import random
import time
from typing import TYPE_CHECKING

from memos.configs.embedder import FallbackConfig, OllamaEmbedderConfig
from memos.embedders.base import BaseEmbedder
from memos.exceptions import (
    EmbedderError,
    EmbeddingDimensionMismatchError,
    PermanentEmbedderError,
    TransientEmbedderError,
)
from memos.log import get_logger


if TYPE_CHECKING:
    from memos.configs.embedder import BaseEmbedderConfig

logger = get_logger(__name__)


# =============================================================================
# Error Classification
# =============================================================================

# HTTP status codes that indicate transient errors (can be retried)
TRANSIENT_STATUS_CODES = {
    408,  # Request Timeout
    429,  # Too Many Requests
    500,  # Internal Server Error
    502,  # Bad Gateway
    503,  # Service Unavailable
    504,  # Gateway Timeout
}

# HTTP status codes that indicate permanent errors (immediate fallback)
PERMANENT_STATUS_CODES = {
    401,  # Unauthorized
    403,  # Forbidden
    404,  # Not Found
    422,  # Unprocessable Entity
}

# Error messages that indicate transient errors
TRANSIENT_ERROR_KEYWORDS = [
    "timeout",
    "timed out",
    "connection reset",
    "connection refused",
    "temporarily unavailable",
    "rate limit",
    "too many requests",
    "server error",
    "bad gateway",
    "service unavailable",
    "gateway timeout",
]

# Error messages that indicate permanent errors
PERMANENT_ERROR_KEYWORDS = [
    "unauthorized",
    "invalid api key",
    "api key invalid",
    "authentication failed",
    "forbidden",
    "not found",
    "model not found",
    "invalid model",
    "unprocessable",
]


def _extract_status_code(error: Exception) -> int | None:
    """Extract HTTP status code from an exception if available."""
    # OpenAI exceptions
    if hasattr(error, "status_code"):
        return error.status_code

    # httpx/requests exceptions
    if hasattr(error, "response") and hasattr(error.response, "status_code"):
        return error.response.status_code

    # Check string representation for status codes
    error_str = str(error).lower()
    for code in TRANSIENT_STATUS_CODES | PERMANENT_STATUS_CODES:
        if str(code) in error_str:
            return code

    return None


def classify_error(error: Exception) -> type[EmbedderError]:
    """
    Classify an error as transient or permanent.

    Args:
        error: The exception to classify.

    Returns:
        TransientEmbedderError for retryable errors,
        PermanentEmbedderError for errors that should trigger immediate fallback.
    """
    # Check if it's already classified
    if isinstance(error, TransientEmbedderError):
        return TransientEmbedderError
    if isinstance(error, PermanentEmbedderError):
        return PermanentEmbedderError

    # Check HTTP status code
    status_code = _extract_status_code(error)
    if status_code:
        if status_code in TRANSIENT_STATUS_CODES:
            return TransientEmbedderError
        if status_code in PERMANENT_STATUS_CODES:
            return PermanentEmbedderError

    # Check error message keywords
    error_str = str(error).lower()

    for keyword in PERMANENT_ERROR_KEYWORDS:
        if keyword in error_str:
            return PermanentEmbedderError

    for keyword in TRANSIENT_ERROR_KEYWORDS:
        if keyword in error_str:
            return TransientEmbedderError

    # Connection errors are typically transient
    if isinstance(error, (ConnectionError, TimeoutError, OSError)):
        return TransientEmbedderError

    # Default to transient for unknown errors (safer to retry)
    return TransientEmbedderError


# =============================================================================
# Retry Policy
# =============================================================================

class RetryPolicy:
    """Exponential backoff retry policy with optional jitter."""

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay_ms: int = 1000,
        max_delay_ms: int = 30000,
        backoff_multiplier: float = 2.0,
        jitter: bool = True,
    ):
        self.max_retries = max_retries
        self.initial_delay_ms = initial_delay_ms
        self.max_delay_ms = max_delay_ms
        self.backoff_multiplier = backoff_multiplier
        self.jitter = jitter

    def get_delay_ms(self, attempt: int) -> int:
        """
        Calculate delay for a given retry attempt.

        Args:
            attempt: The current retry attempt (1-indexed).

        Returns:
            Delay in milliseconds.
        """
        # Calculate base delay with exponential backoff
        delay = self.initial_delay_ms * (self.backoff_multiplier ** (attempt - 1))

        # Apply max delay cap
        delay = min(delay, self.max_delay_ms)

        # Add jitter (±25% randomness)
        if self.jitter:
            jitter_factor = 0.75 + random.random() * 0.5
            delay = delay * jitter_factor

        return int(delay)

    def should_retry(self, attempt: int) -> bool:
        """Check if another retry attempt should be made."""
        return attempt < self.max_retries


# =============================================================================
# Dimension Adapter
# =============================================================================

class DimensionAdapter:
    """
    Handles embedding dimension mismatches between primary and fallback embedders.
    """

    def __init__(
        self,
        primary_dims: int | None,
        fallback_dims: int | None,
        strategy: str = "error",
    ):
        self.primary_dims = primary_dims
        self.fallback_dims = fallback_dims
        self.strategy = strategy
        self._warned = False

    def adapt(self, embeddings: list[list[float]]) -> list[list[float]]:
        """
        Adapt embeddings to match expected dimensions.

        Args:
            embeddings: List of embeddings from fallback embedder.

        Returns:
            Adapted embeddings.

        Raises:
            EmbeddingDimensionMismatchError: If strategy is 'error' and dimensions mismatch.
        """
        if not embeddings:
            return embeddings

        actual_dims = len(embeddings[0]) if embeddings[0] else 0

        # If primary dims not specified, we can't validate
        if self.primary_dims is None:
            return embeddings

        # Dimensions match, no adaptation needed
        if actual_dims == self.primary_dims:
            return embeddings

        # Handle mismatch based on strategy
        if self.strategy == "error":
            raise EmbeddingDimensionMismatchError(
                f"Embedding dimension mismatch: expected {self.primary_dims}, "
                f"got {actual_dims} from fallback embedder. "
                f"Set MOS_EMBEDDER_FALLBACK_DIMENSION_STRATEGY to 'warn_and_continue' "
                f"or 'pad_or_truncate' to handle this automatically."
            )

        elif self.strategy == "warn_and_continue":
            if not self._warned:
                logger.warning(
                    f"Embedding dimension mismatch: expected {self.primary_dims}, "
                    f"got {actual_dims}. Returning as-is (may cause issues with vector DB)."
                )
                self._warned = True
            return embeddings

        elif self.strategy == "pad_or_truncate":
            if not self._warned:
                logger.warning(
                    f"Embedding dimension mismatch: expected {self.primary_dims}, "
                    f"got {actual_dims}. Adapting dimensions (may affect similarity accuracy)."
                )
                self._warned = True
            return self._pad_or_truncate(embeddings, self.primary_dims)

        else:
            raise ValueError(f"Unknown dimension mismatch strategy: {self.strategy}")

    def _pad_or_truncate(
        self, embeddings: list[list[float]], target_dims: int
    ) -> list[list[float]]:
        """Pad with zeros or truncate embeddings to target dimensions."""
        adapted = []
        for emb in embeddings:
            if len(emb) < target_dims:
                # Pad with zeros
                adapted.append(emb + [0.0] * (target_dims - len(emb)))
            elif len(emb) > target_dims:
                # Truncate
                adapted.append(emb[:target_dims])
            else:
                adapted.append(emb)
        return adapted


# =============================================================================
# Fallback Embedder
# =============================================================================

class FallbackEmbedder(BaseEmbedder):
    """
    Wrapper embedder that provides automatic fallback to a backup embedder.

    This embedder:
    1. Attempts to use the primary embedder
    2. On transient errors, retries with exponential backoff
    3. On permanent errors or retry exhaustion, falls back to backup embedder
    4. Handles embedding dimension mismatches based on configured strategy
    """

    def __init__(
        self,
        primary: BaseEmbedder,
        fallback_config: FallbackConfig,
        primary_config: "BaseEmbedderConfig | None" = None,
    ):
        """
        Initialize the fallback embedder.

        Args:
            primary: The primary embedder to use.
            fallback_config: Configuration for fallback behavior.
            primary_config: Optional config of primary embedder for dimension info.
        """
        self.primary = primary
        self.fallback_config = fallback_config
        self.primary_config = primary_config

        # Store primary embedder's config as our own config
        self.config = getattr(primary, "config", None)

        # Initialize retry policy
        self.retry_policy = RetryPolicy(
            max_retries=fallback_config.max_retries,
            initial_delay_ms=fallback_config.initial_delay_ms,
            max_delay_ms=fallback_config.max_delay_ms,
            backoff_multiplier=fallback_config.backoff_multiplier,
            jitter=fallback_config.jitter,
        )

        # Lazy-initialized fallback embedder
        self._fallback: BaseEmbedder | None = None

        # Track primary embedder health
        self._primary_healthy = True
        self._consecutive_failures = 0

        # Dimension adapter (lazy-initialized when needed)
        self._dimension_adapter: DimensionAdapter | None = None

        logger.info(
            f"FallbackEmbedder initialized: "
            f"max_retries={fallback_config.max_retries}, "
            f"fallback_backend={fallback_config.fallback_backend}, "
            f"dimension_strategy={fallback_config.dimension_mismatch_strategy}"
        )

    @property
    def fallback(self) -> BaseEmbedder:
        """Lazy-load the fallback embedder."""
        if self._fallback is None:
            self._fallback = self._create_fallback_embedder()
        return self._fallback

    def _create_fallback_embedder(self) -> BaseEmbedder:
        """Create the fallback embedder based on configuration."""
        from memos.embedders.ollama import OllamaEmbedder

        cfg = self.fallback_config

        if cfg.fallback_backend == "ollama":
            fallback_config = OllamaEmbedderConfig(
                model_name_or_path=cfg.fallback_model,
                api_base=cfg.fallback_api_base,
                embedding_dims=cfg.fallback_embedding_dims,
                max_tokens=self.config.max_tokens if self.config else None,
            )
            logger.info(
                f"Creating Ollama fallback embedder: "
                f"model={cfg.fallback_model}, api_base={cfg.fallback_api_base}"
            )
            return OllamaEmbedder(fallback_config)
        else:
            raise ValueError(
                f"Unsupported fallback backend: {cfg.fallback_backend}. "
                f"Currently only 'ollama' is supported."
            )

    def _get_dimension_adapter(self) -> DimensionAdapter:
        """Get or create the dimension adapter."""
        if self._dimension_adapter is None:
            primary_dims = None
            if self.config and hasattr(self.config, "embedding_dims"):
                primary_dims = self.config.embedding_dims

            fallback_dims = self.fallback_config.fallback_embedding_dims

            self._dimension_adapter = DimensionAdapter(
                primary_dims=primary_dims,
                fallback_dims=fallback_dims,
                strategy=self.fallback_config.dimension_mismatch_strategy,
            )
        return self._dimension_adapter

    def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings with automatic retry and fallback.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embeddings.

        Raises:
            EmbedderError: If both primary and fallback fail.
        """
        if not texts:
            return []

        # Try primary embedder with retries
        last_error: Exception | None = None

        for attempt in range(1, self.retry_policy.max_retries + 2):  # +1 for initial + retries
            try:
                result = self.primary.embed(texts)
                # Success - reset failure counter
                if self._consecutive_failures > 0:
                    logger.info("Primary embedder recovered after fallback")
                    self._consecutive_failures = 0
                    self._primary_healthy = True
                return result

            except Exception as e:
                last_error = e
                error_type = classify_error(e)

                # Log the error
                if attempt == 1:
                    logger.warning(
                        f"Primary embedder failed (attempt {attempt}): {type(e).__name__}: {e}"
                    )
                else:
                    logger.warning(
                        f"Primary embedder retry {attempt - 1} failed: {type(e).__name__}: {e}"
                    )

                # Permanent error - skip retries, go straight to fallback
                if error_type == PermanentEmbedderError:
                    logger.warning(
                        f"Permanent error detected, skipping retries: {type(e).__name__}"
                    )
                    break

                # Check if we should retry
                if not self.retry_policy.should_retry(attempt):
                    logger.warning(
                        f"Max retries ({self.retry_policy.max_retries}) exhausted"
                    )
                    break

                # Wait before retry
                delay_ms = self.retry_policy.get_delay_ms(attempt)
                logger.info(f"Waiting {delay_ms}ms before retry {attempt}...")
                time.sleep(delay_ms / 1000.0)

        # All retries failed - use fallback
        self._consecutive_failures += 1
        self._primary_healthy = False

        logger.warning(
            f"Falling back to {self.fallback_config.fallback_backend} embedder "
            f"(consecutive failures: {self._consecutive_failures})"
        )

        try:
            result = self.fallback.embed(texts)

            # Adapt dimensions if needed
            adapter = self._get_dimension_adapter()
            result = adapter.adapt(result)

            return result

        except Exception as fallback_error:
            # Both primary and fallback failed
            logger.error(
                f"Fallback embedder also failed: {type(fallback_error).__name__}: {fallback_error}"
            )

            # Raise the original primary error (more informative usually)
            if last_error:
                raise EmbedderError(
                    f"Both primary and fallback embedders failed. "
                    f"Primary error: {last_error}. "
                    f"Fallback error: {fallback_error}"
                ) from last_error
            raise

    def is_primary_healthy(self) -> bool:
        """Check if the primary embedder is currently healthy."""
        return self._primary_healthy

    def get_consecutive_failures(self) -> int:
        """Get the number of consecutive primary embedder failures."""
        return self._consecutive_failures


def wrap_with_fallback(
    primary: BaseEmbedder,
    fallback_config: FallbackConfig,
    primary_config: "BaseEmbedderConfig | None" = None,
) -> BaseEmbedder:
    """
    Wrap an embedder with fallback support if enabled.

    Args:
        primary: The primary embedder.
        fallback_config: Fallback configuration.
        primary_config: Optional primary embedder config for dimension info.

    Returns:
        FallbackEmbedder if fallback is enabled, otherwise the original embedder.
    """
    if fallback_config.enabled:
        return FallbackEmbedder(primary, fallback_config, primary_config)
    return primary
