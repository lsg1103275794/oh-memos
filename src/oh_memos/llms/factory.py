from typing import Any, ClassVar

from oh_memos.configs.llm import LLMConfigFactory
from oh_memos.llms.base import BaseLLM
from oh_memos.llms.deepseek import DeepSeekLLM
from oh_memos.llms.hf import HFLLM
from oh_memos.llms.hf_singleton import HFSingletonLLM
from oh_memos.llms.ollama import OllamaLLM
from oh_memos.llms.openai import AzureLLM, OpenAILLM
from oh_memos.llms.openai_new import OpenAIResponsesLLM
from oh_memos.llms.qwen import QwenLLM
from oh_memos.llms.vllm import VLLMLLM
from oh_memos.memos_tools.singleton import singleton_factory


class LLMFactory(BaseLLM):
    """Factory class for creating LLM instances."""

    backend_to_class: ClassVar[dict[str, Any]] = {
        "openai": OpenAILLM,
        "azure": AzureLLM,
        "ollama": OllamaLLM,
        "huggingface": HFLLM,
        "huggingface_singleton": HFSingletonLLM,  # Add singleton version
        "vllm": VLLMLLM,
        "qwen": QwenLLM,
        "deepseek": DeepSeekLLM,
        "openai_new": OpenAIResponsesLLM,
    }

    @classmethod
    @singleton_factory()
    def from_config(cls, config_factory: LLMConfigFactory) -> BaseLLM:
        backend = config_factory.backend
        if backend not in cls.backend_to_class:
            raise ValueError(f"Invalid backend: {backend}")
        llm_class = cls.backend_to_class[backend]
        return llm_class(config_factory.config)
