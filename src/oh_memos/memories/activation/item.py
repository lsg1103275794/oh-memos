import uuid

from datetime import datetime
from typing import Annotated, Any

from pydantic import AfterValidator, BaseModel, Field

from oh_memos.mem_scheduler.utils.db_utils import get_utc_now


class ActivationMemoryItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    memory: Any
    metadata: dict = {}


class KVCacheRecords(BaseModel):
    text_memories: list[str] = Field(
        default=[],
        description="The list of text memories transformed to the activation memory.",
    )
    composed_text_memory: str = Field(
        default="",
        description="Single string combining all text_memories using assembly template",
    )
    timestamp: datetime = Field(
        default_factory=get_utc_now, description="submit time for schedule_messages"
    )


# transformers imports torch, and this module sits on the import path of every process
# (oh_memos.types). DynamicCache is therefore resolved only when a KV cache is built.
def _new_dynamic_cache() -> Any:
    from transformers import DynamicCache

    return DynamicCache()


def _require_dynamic_cache(value: Any) -> Any:
    from transformers import DynamicCache

    if not isinstance(value, DynamicCache):
        raise ValueError(f"memory must be a transformers DynamicCache, got {type(value).__name__}")
    return value


class KVCacheItem(ActivationMemoryItem):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    memory: Annotated[Any, AfterValidator(_require_dynamic_cache)] = Field(
        default_factory=_new_dynamic_cache,
        description="Dynamic cache for storing key-value pairs in the memory.",
    )
    metadata: dict = Field(
        default_factory=dict, description="Metadata associated with the KV cache item."
    )

    records: KVCacheRecords = KVCacheRecords()


class VLLMKVCacheItem(KVCacheItem):
    """
    VLLM KV Cache Item that stores prompt strings instead of DynamicCache objects.
    This is because vLLM handles KV cache on the server side via preloading.
    """

    # Override memory field to store prompt string instead of DynamicCache
    memory: str = Field(
        default="",
        description="Prompt string used to preload KV cache in vLLM server",
    )
