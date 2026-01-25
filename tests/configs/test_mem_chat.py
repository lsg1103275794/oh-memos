from memos.configs.mem_chat import (
    BaseMemChatConfig,
    MemChatConfigFactory,
    SimpleMemChatConfig,
)
from tests.utils import (
    check_config_base_class,
    check_config_instantiation_invalid,
    check_config_instantiation_valid,
)


def test_base_mem_chat_config():
    check_config_base_class(
        BaseMemChatConfig,
        factory_fields=["session_id", "created_at"],
        required_fields=["user_id"],
        optional_fields=["config_filename"],
    )

    check_config_instantiation_valid(
        BaseMemChatConfig,
        {
            "user_id": "test_user",
            "session_id": "test_session",
        },
    )

    check_config_instantiation_invalid(BaseMemChatConfig)


def test_simple_mem_chat_config():
    check_config_base_class(
        SimpleMemChatConfig,
        factory_fields=["session_id", "chat_llm", "created_at", "chat_llm"],
        required_fields=["user_id"],
        optional_fields=[
            "config_filename",
            "max_turns_window",
            "top_k",
            "enable_textual_memory",
            "enable_activation_memory",
            "enable_parametric_memory",
        ],
    )

    check_config_instantiation_valid(
        SimpleMemChatConfig,
        {
            "user_id": "test_user",
            "session_id": "test_session",
            "chat_llm": {
                "backend": "ollama",
                "config": {
                    "model_name_or_path": "test-model",
                },
            },
        },
    )

    check_config_instantiation_invalid(SimpleMemChatConfig)


def test_mem_chat_config_factory():
    check_config_base_class(
        MemChatConfigFactory,
        required_fields=["backend", "config"],
        optional_fields=[],
    )

    check_config_instantiation_valid(
        MemChatConfigFactory,
        {
            "backend": "simple",
            "config": {
                "user_id": "test_user",
                "session_id": "test_session",
                "chat_llm": {
                    "backend": "ollama",
                    "config": {
                        "model_name_or_path": "test-model",
                    },
                },
            },
        },
    )

    check_config_instantiation_invalid(MemChatConfigFactory)
