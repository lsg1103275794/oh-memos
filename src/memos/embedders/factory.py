from typing import Any, ClassVar

from memos.configs.embedder import EmbedderConfigFactory, FallbackConfig
from memos.configs.env_loader import get_embedder_fallback_config
from memos.embedders.ark import ArkEmbedder
from memos.embedders.base import BaseEmbedder
from memos.embedders.fallback import FallbackEmbedder
from memos.embedders.ollama import OllamaEmbedder
from memos.embedders.sentence_transformer import SenTranEmbedder
from memos.embedders.universal_api import UniversalAPIEmbedder
from memos.log import get_logger
from memos.memos_tools.singleton import singleton_factory


logger = get_logger(__name__)


class EmbedderFactory(BaseEmbedder):
    """Factory class for creating embedder instances."""

    backend_to_class: ClassVar[dict[str, Any]] = {
        "ollama": OllamaEmbedder,
        "sentence_transformer": SenTranEmbedder,
        "ark": ArkEmbedder,
        "universal_api": UniversalAPIEmbedder,
    }

    @classmethod
    def _get_fallback_config(cls) -> FallbackConfig | None:
        """
        Get fallback configuration from environment.

        Returns:
            FallbackConfig if fallback is enabled, None otherwise.
        """
        try:
            cfg_dict = get_embedder_fallback_config()
            if cfg_dict.get("enabled", False):
                return FallbackConfig(**cfg_dict)
            return None
        except Exception as e:
            logger.warning(f"Failed to load fallback config: {e}")
            return None

    @classmethod
    def _wrap_with_fallback(
        cls,
        primary: BaseEmbedder,
        fallback_config: FallbackConfig,
        config_factory: EmbedderConfigFactory,
    ) -> BaseEmbedder:
        """
        Wrap an embedder with fallback support.

        Args:
            primary: The primary embedder instance.
            fallback_config: Fallback configuration.
            config_factory: The original embedder config factory.

        Returns:
            FallbackEmbedder wrapping the primary embedder.
        """
        logger.info(
            f"Wrapping embedder with fallback support: "
            f"backend={fallback_config.fallback_backend}, "
            f"model={fallback_config.fallback_model}"
        )
        return FallbackEmbedder(
            primary=primary,
            fallback_config=fallback_config,
            primary_config=config_factory.config,
        )

    @classmethod
    @singleton_factory()
    def from_config(cls, config_factory: EmbedderConfigFactory) -> BaseEmbedder:
        backend = config_factory.backend
        if backend not in cls.backend_to_class:
            raise ValueError(f"Invalid backend: {backend}")
        embedder_class = cls.backend_to_class[backend]
        primary = embedder_class(config_factory.config)

        # Check if fallback is enabled
        fallback_config = cls._get_fallback_config()
        if fallback_config:
            return cls._wrap_with_fallback(primary, fallback_config, config_factory)

        return primary
