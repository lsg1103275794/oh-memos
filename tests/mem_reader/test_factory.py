from memos.configs.mem_reader import MemReaderConfigFactory
from memos.mem_reader.factory import MemReaderFactory
from memos.mem_reader.simple_struct import SimpleStructMemReader
from tests.utils import check_module_factory_class


def test_factory_class():
    """Test the MemReaderFactory class structure."""
    check_module_factory_class(MemReaderFactory)


def test_factory_from_config():
    """Test factory.from_config method for creating MemReader instances."""
    # Test with naive backend
    config_factory = MemReaderConfigFactory(
        backend="simple_struct",
        config={
            "llm": {
                "backend": "ollama",
                "config": {
                    "model_name_or_path": "qwen3:0.6b",
                    "temperature": 0.8,
                    "max_tokens": 1024,
                    "top_p": 0.9,
                    "top_k": 50,
                },
            },
            "embedder": {
                "backend": "ollama",
                "config": {
                    "model_name_or_path": "nomic-embed-text:latest",
                },
            },
            "chunker": {
                "backend": "sentence",
                "config": {
                    "tokenizer_or_token_counter": "gpt2",
                    "chunk_size": 512,
                    "chunk_overlap": 128,
                    "min_sentences_per_chunk": 1,
                },
            },
        },
    )

    mem_reader = MemReaderFactory.from_config(config_factory)
    assert isinstance(mem_reader, SimpleStructMemReader)
