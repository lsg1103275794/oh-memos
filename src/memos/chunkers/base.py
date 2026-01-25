from abc import ABC, abstractmethod

from memos.configs.chunker import BaseChunkerConfig


class Chunk:
    """Class representing a text chunk."""

    def __init__(self, text: str, token_count: int, sentences: list[str]):
        self.text = text
        self.token_count = token_count
        self.sentences = sentences


class BaseChunker(ABC):
    """Base class for all text chunkers."""

    @abstractmethod
    def __init__(self, config: BaseChunkerConfig):
        """Initialize the chunker with the given configuration."""

    @abstractmethod
    def chunk(self, text: str) -> list[Chunk]:
        """Chunk the given text into smaller chunks."""
