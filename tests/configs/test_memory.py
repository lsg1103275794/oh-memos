from memos.configs.memory import (
    BaseActMemoryConfig,
    BaseMemoryConfig,
    BaseParaMemoryConfig,
    BaseTextMemoryConfig,
    GeneralTextMemoryConfig,
    KVCacheMemoryConfig,
    LoRAMemoryConfig,
    MemoryConfigFactory,
    NaiveTextMemoryConfig,
)
from tests.utils import (
    check_config_base_class,
    check_config_factory_class,
    check_config_instantiation_invalid,
    check_config_instantiation_valid,
)


def test_base_memory_config():
    check_config_base_class(
        BaseMemoryConfig,
        required_fields=[],
        optional_fields=["cube_id"],
    )

    check_config_instantiation_valid(
        BaseMemoryConfig,
        {},
    )

    check_config_instantiation_invalid(BaseMemoryConfig)


def test_base_act_memory_config():
    check_config_base_class(
        BaseActMemoryConfig,
        required_fields=[],
        optional_fields=["cube_id", "memory_filename"],
    )

    check_config_instantiation_valid(
        BaseActMemoryConfig,
        {},
    )

    check_config_instantiation_invalid(BaseActMemoryConfig)


def test_kv_cache_memory_config():
    check_config_base_class(
        KVCacheMemoryConfig,
        factory_fields=["extractor_llm"],
        required_fields=[],
        optional_fields=["cube_id", "memory_filename"],
    )

    check_config_instantiation_valid(
        KVCacheMemoryConfig,
        {
            "extractor_llm": {
                "backend": "huggingface",
                "config": {
                    "model_name_or_path": "test-model",
                },
            },
        },
    )

    check_config_instantiation_invalid(KVCacheMemoryConfig)


def test_base_para_memory_config():
    check_config_base_class(
        BaseParaMemoryConfig,
        required_fields=[],
        optional_fields=["cube_id", "memory_filename"],
    )

    check_config_instantiation_valid(
        BaseParaMemoryConfig,
        {},
    )

    check_config_instantiation_invalid(BaseParaMemoryConfig)


def test_lora_memory_config():
    check_config_base_class(
        LoRAMemoryConfig,
        factory_fields=["extractor_llm"],
        required_fields=[],
        optional_fields=["cube_id", "memory_filename"],
    )

    check_config_instantiation_valid(
        LoRAMemoryConfig,
        {
            "extractor_llm": {
                "backend": "huggingface",
                "config": {
                    "model_name_or_path": "test-model",
                },
            },
        },
    )

    check_config_instantiation_valid(
        LoRAMemoryConfig,
        {
            "extractor_llm": {
                "backend": "huggingface",
                "config": {
                    "model_name_or_path": "test-model",
                },
            },
        },
    )

    check_config_instantiation_invalid(LoRAMemoryConfig)


def test_base_text_memory_config():
    check_config_base_class(
        BaseTextMemoryConfig,
        required_fields=[],
        optional_fields=["cube_id", "memory_filename"],
    )

    check_config_instantiation_valid(
        BaseTextMemoryConfig,
        {},
    )

    check_config_instantiation_invalid(BaseTextMemoryConfig)


def test_naive_memory_config():
    check_config_base_class(
        NaiveTextMemoryConfig,
        factory_fields=["extractor_llm"],
        required_fields=[],
        optional_fields=["cube_id", "memory_filename"],
    )

    check_config_instantiation_valid(
        NaiveTextMemoryConfig,
        {
            "extractor_llm": {
                "backend": "ollama",
                "config": {
                    "model_name_or_path": "test-model",
                },
            },
        },
    )

    check_config_instantiation_invalid(NaiveTextMemoryConfig)


def test_textual_memory_config():
    check_config_base_class(
        GeneralTextMemoryConfig,
        factory_fields=[
            "extractor_llm",
            "vector_db",
            "embedder",
        ],
        required_fields=[],
        optional_fields=["cube_id", "memory_filename"],
    )

    check_config_instantiation_valid(
        GeneralTextMemoryConfig,
        {
            "extractor_llm": {
                "backend": "ollama",
                "config": {
                    "model_name_or_path": "test-model",
                },
            },
            "vector_db": {
                "backend": "qdrant",
                "config": {
                    "collection_name": "test_collection",
                },
            },
            "embedder": {
                "backend": "ollama",
                "config": {
                    "model_name_or_path": "test-embedder",
                },
            },
        },
    )

    check_config_instantiation_invalid(GeneralTextMemoryConfig)


def test_memory_config_factory():
    check_config_factory_class(
        MemoryConfigFactory,
        expected_backends=["naive_text", "general_text"],
    )

    check_config_instantiation_valid(
        MemoryConfigFactory,
        {
            "backend": "naive_text",
            "config": {
                "extractor_llm": {
                    "backend": "ollama",
                    "config": {
                        "model_name_or_path": "test-model",
                    },
                },
            },
        },
    )

    check_config_instantiation_invalid(MemoryConfigFactory)
