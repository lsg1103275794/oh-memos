import json
import uuid

from unittest.mock import MagicMock, patch

import pytest

from memos.configs.memory import NaiveTextMemoryConfig
from memos.llms.factory import LLMFactory
from memos.memories.textual.item import TextualMemoryItem, TextualMemoryMetadata
from memos.memories.textual.naive import NaiveTextMemory


class TestNaiveMemory:
    @pytest.fixture
    def mock_llm(self):
        mock_llm = MagicMock()
        mock_llm.generate.return_value = json.dumps(
            [
                {"memory": "User loves tomatoes", "metadata": {"type": "opinion"}},
                {
                    "memory": "Assistant thinks tomatoes are delicious",
                    "metadata": {"type": "opinion"},
                },
            ]
        )
        return mock_llm

    @pytest.fixture
    def config(self):
        return NaiveTextMemoryConfig(
            extractor_llm={
                "backend": "ollama",
                "config": {
                    "model_name_or_path": "qwen3:0.6b",
                    "temperature": 0.0,
                },
            }
        )

    @pytest.fixture
    def memory(self, config, mock_llm):
        with patch.object(LLMFactory, "from_config", return_value=mock_llm):
            return NaiveTextMemory(config)

    def test_init(self, config):
        with patch.object(LLMFactory, "from_config") as mock_factory:
            memory = NaiveTextMemory(config)
            mock_factory.assert_called_once_with(config.extractor_llm)
            assert memory.memories == []
            assert memory.config == config

    def test_extract(self, memory):
        messages = [
            {"role": "user", "content": "I love tomatoes."},
            {"role": "assistant", "content": "Great! Tomatoes are delicious."},
        ]

        result = memory.extract(messages)

        assert isinstance(result, list)
        assert isinstance(result[0], TextualMemoryItem)
        assert result[0].memory
        assert result[0].metadata

    def test_add(self, memory):
        # Test adding memories
        memory_id = str(uuid.uuid4())
        memories = [
            {"id": memory_id, "memory": "User loves tomatoes", "metadata": {"type": "opinion"}}
        ]
        memory.add(memories)
        assert len(memory.memories) == 1
        assert memory.memories[0]["id"] == memory_id

        # Test duplicate prevention
        memory.add(memories)
        assert len(memory.memories) == 1

        # Test adding multiple memories
        memory_id2 = str(uuid.uuid4())
        memories2 = [
            {"id": memory_id2, "memory": "User dislikes broccoli", "metadata": {"type": "opinion"}}
        ]
        memory.add(memories2)
        assert len(memory.memories) == 2

    def test_update(self, memory):
        memory_id = str(uuid.uuid4())
        original_memory = {
            "id": memory_id,
            "memory": "Original content",
            "metadata": {"type": "fact"},
        }
        memory.add([original_memory])

        # Create TextualMemoryItem for update
        updated_memory = TextualMemoryItem(
            id=memory_id, memory="Updated content", metadata=TextualMemoryMetadata(type="opinion")
        )
        memory.update(memory_id, updated_memory)

        result = memory.get(memory_id)
        assert result.memory == "Updated content"
        assert result.metadata.type == "opinion"

    def test_update_dict(self, memory):
        """Test updating memory using dictionary format."""
        memory_id = str(uuid.uuid4())
        original_memory = {
            "id": memory_id,
            "memory": "Original content",
            "metadata": {"type": "fact"},
        }
        memory.add([original_memory])

        # Update using dictionary format
        updated_memory_dict = {
            "id": memory_id,
            "memory": "Updated content via dict",
            "metadata": {"type": "opinion", "confidence": 85.0},
        }
        memory.update(memory_id, updated_memory_dict)

        result = memory.get(memory_id)
        assert result.memory == "Updated content via dict"
        assert result.metadata.type == "opinion"
        assert result.metadata.confidence == 85.0

    def test_search(self, memory):
        memory_id1 = str(uuid.uuid4())
        memory_id2 = str(uuid.uuid4())
        memory1 = {
            "id": memory_id1,
            "memory": "User loves tomatoes",
            "metadata": {"type": "opinion"},
        }
        memory2 = {
            "id": memory_id2,
            "memory": "User dislikes broccoli",
            "metadata": {"type": "opinion"},
        }

        memory.add([memory1, memory2])

        # Test search with exact match
        result = memory.search("User loves tomatoes", top_k=1)
        assert len(result) == 1
        assert result[0].id == memory_id1

        # Test search with partial match
        result = memory.search("User loves", top_k=2)
        assert len(result) == 2
        assert result[0].id == memory_id1
        assert result[1].id == memory_id2

        # Test search with no matches
        result = memory.search("non_existent_query", top_k=1)
        assert len(result) == 1

    def test_get(self, memory):
        memory_id = str(uuid.uuid4())
        test_memory = {"id": memory_id, "memory": "Test content", "metadata": {"type": "fact"}}
        memory.add([test_memory])

        result = memory.get(memory_id)
        assert result.id == memory_id
        assert result.memory == "Test content"
        assert result.metadata.type == "fact"

        # Test non-existent memory
        non_existent_id = str(uuid.uuid4())
        result = memory.get(non_existent_id)
        assert result.id == non_existent_id
        assert result.memory == ""

    def test_get_all(self, memory):
        # Test with empty memories
        assert memory.get_all() == []

        # Test with memories
        memory_id1 = str(uuid.uuid4())
        memory_id2 = str(uuid.uuid4())
        memory1 = {"id": memory_id1, "memory": "Memory 1", "metadata": {"type": "fact"}}
        memory2 = {"id": memory_id2, "memory": "Memory 2", "metadata": {"type": "opinion"}}

        memory.add([memory1, memory2])
        result = memory.get_all()

        assert len(result) == 2

        # Check that all IDs are present in the result
        result_ids = [item.id for item in result]
        assert memory_id1 in result_ids
        assert memory_id2 in result_ids

        # Check memories by content
        memories_content = {item.id: item.memory for item in result}
        assert memories_content[memory_id1] == "Memory 1"
        assert memories_content[memory_id2] == "Memory 2"

        # Check metadata types
        memories_types = {item.id: item.metadata.type for item in result}
        assert memories_types[memory_id1] == "fact"
        assert memories_types[memory_id2] == "opinion"

    def test_delete(self, memory):
        memory_id1 = str(uuid.uuid4())
        memory_id2 = str(uuid.uuid4())
        memory1 = {"id": memory_id1, "memory": "Memory 1", "metadata": {"type": "fact"}}
        memory2 = {"id": memory_id2, "memory": "Memory 2", "metadata": {"type": "opinion"}}

        memory.add([memory1, memory2])
        assert len(memory.memories) == 2

        memory.delete([memory_id1])
        assert len(memory.memories) == 1
        assert memory.memories[0]["id"] == memory_id2

        # Test deleting non-existent memory (should have no effect)
        memory.delete([str(uuid.uuid4())])
        assert len(memory.memories) == 1

    def test_delete_all(self, memory):
        memories = [
            {"id": str(uuid.uuid4()), "memory": "Memory 1", "metadata": {"type": "fact"}},
            {"id": str(uuid.uuid4()), "memory": "Memory 2", "metadata": {"type": "opinion"}},
        ]
        memory.add(memories)
        assert len(memory.memories) == 2

        memory.delete_all()
        assert memory.memories == []

    def test_load_and_dump(self, memory, tmp_path):
        """Test load and dump functionality."""
        # Add some test memories
        test_memories = [
            {"id": str(uuid.uuid4()), "memory": "Test memory 1", "metadata": {"type": "fact"}},
            {"id": str(uuid.uuid4()), "memory": "Test memory 2", "metadata": {"type": "opinion"}},
        ]
        memory.add(test_memories)

        # Dump memories to temporary directory
        test_dir = str(tmp_path)
        memory.dump(test_dir)

        # Create a new memory instance and load the dumped data
        new_memory = NaiveTextMemory(memory.config)
        new_memory.load(test_dir)

        # Verify that loaded memories match original memories
        assert len(new_memory.memories) == 2
        loaded_memory_ids = {m["id"] for m in new_memory.memories}
        original_memory_ids = {m["id"] for m in test_memories}
        assert loaded_memory_ids == original_memory_ids

    def test_load_nonexistent_directory(self, memory, caplog):
        """Test loading from a non-existent directory."""
        nonexistent_dir = "/nonexistent/path"
        memory.load(nonexistent_dir)

        # Check that error was logged but no exception was raised
        assert "Directory not found" in caplog.text
        assert len(memory.memories) == 0
