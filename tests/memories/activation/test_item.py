import uuid

from transformers import DynamicCache

from memos.memories.activation.item import ActivationMemoryItem, KVCacheItem


class TestActivationMemoryItem:
    def test_basic_init_and_defaults(self):
        # Test initialization and default values
        item = ActivationMemoryItem(memory="test-activation", metadata={"foo": "bar"})
        assert item.id is not None
        assert item.memory == "test-activation"
        assert isinstance(item.metadata, dict)

    def test_id_is_uuid(self):
        # Test that id is a valid UUID
        item = ActivationMemoryItem(memory="abc")
        uuid.UUID(item.id)  # Should not raise

    def test_metadata_default(self):
        # Test that metadata defaults to an empty dict
        item = ActivationMemoryItem(memory="abc")
        assert item.metadata == {}


class TestKVCacheItem:
    def test_kvcacheitem_init_and_types(self):
        # Test initialization and types for KVCacheItem
        cache = DynamicCache()
        item = KVCacheItem(memory=cache, metadata={"layer": 1})
        assert isinstance(item.memory, DynamicCache)
        assert item.metadata["layer"] == 1
        uuid.UUID(item.id)

    def test_metadata_default(self):
        # Test that metadata defaults to an empty dict for KVCacheItem
        item = KVCacheItem()
        assert isinstance(item.memory, DynamicCache)
        assert item.metadata == {}

    def test_arbitrary_types_allowed(self):
        # Test that arbitrary types (DynamicCache) are allowed as memory
        cache = DynamicCache()
        item = KVCacheItem(memory=cache)
        assert isinstance(item.memory, DynamicCache)
