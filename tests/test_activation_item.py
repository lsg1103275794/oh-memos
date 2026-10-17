"""KV-cache items keep their DynamicCache contract while transformers loads lazily."""

import pytest

from pydantic import ValidationError

from oh_memos.memories.activation.item import KVCacheItem, VLLMKVCacheItem


@pytest.fixture
def dynamic_cache_cls():
    transformers = pytest.importorskip("transformers")
    dynamic_cache = getattr(transformers, "DynamicCache", None)
    if not isinstance(dynamic_cache, type):
        pytest.skip("transformers is stubbed on this host (see conftest.py)")
    return dynamic_cache


def test_default_memory_is_an_empty_dynamic_cache(dynamic_cache_cls):
    assert isinstance(KVCacheItem().memory, dynamic_cache_cls)


@pytest.mark.usefixtures("dynamic_cache_cls")
def test_rejects_memory_that_is_not_a_dynamic_cache():
    with pytest.raises(ValidationError):
        KVCacheItem(memory="not a cache")


def test_vllm_item_still_stores_prompt_strings():
    # Re-declaring `memory: str` must drop the parent's DynamicCache validator
    assert VLLMKVCacheItem.model_fields["memory"].metadata == []
    assert VLLMKVCacheItem(memory="preloaded prompt").memory == "preloaded prompt"
