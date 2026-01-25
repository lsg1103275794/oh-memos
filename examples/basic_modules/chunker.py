from memos.chunkers import ChunkerFactory
from memos.configs.chunker import ChunkerConfigFactory


def main():
    # Create a config factory with sentence chunker backend
    config_factory = ChunkerConfigFactory(
        backend="sentence",
        config={
            "tokenizer_or_token_counter": "gpt2",
            "chunk_size": 10,
            "chunk_overlap": 5,
            "min_sentences_per_chunk": 1,
        },
    )

    # Create a chunker using the factory
    chunker = ChunkerFactory.from_config(config_factory)

    # Example text to chunk
    text = """This is the first sentence. This is the second sentence.
    And here's a third one with some additional context."""

    # Get chunks
    chunks = chunker.chunk(text)

    # Print each chunk's info
    for chunk in chunks:
        print(f"Chunk text: {chunk.text}")
        print(f"Token count: {chunk.token_count}")
        print(f"Number of sentences: {len(chunk.sentences)}")
        print("---")


if __name__ == "__main__":
    main()  # If there are network issues, you can configure: export HF_ENDPOINT=https://hf-mirror.com
