"""Custom exceptions for the MemOS library.

This module defines all custom exceptions used throughout the MemOS project.
All exceptions inherit from a base MemOSError class to provide a consistent
error handling interface.
"""


class MemOSError(Exception): ...


class ConfigurationError(MemOSError): ...


class MemoryError(MemOSError): ...


class MemCubeError(MemOSError): ...


class VectorDBError(MemOSError): ...


class LLMError(MemOSError): ...


class EmbedderError(MemOSError): ...


class TransientEmbedderError(EmbedderError):
    """Transient errors that can be retried: timeout, 429, 500, 503."""

    pass


class PermanentEmbedderError(EmbedderError):
    """Permanent errors that should trigger immediate fallback: 401, 403, 404."""

    pass


class EmbeddingDimensionMismatchError(EmbedderError):
    """Embedding dimension mismatch between primary and fallback embedders."""

    pass


class ParserError(MemOSError): ...
