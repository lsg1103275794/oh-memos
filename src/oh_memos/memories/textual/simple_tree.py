from typing import TYPE_CHECKING

from oh_memos.configs.memory import TreeTextMemoryConfig
from oh_memos.embedders.base import BaseEmbedder
from oh_memos.graph_dbs.base import BaseGraphDB
from oh_memos.llms.base import BaseLLM
from oh_memos.log import get_logger
from oh_memos.mem_reader.base import BaseMemReader
from oh_memos.memories.textual.tree import TreeTextMemory
from oh_memos.memories.textual.tree_text_memory.organize.manager import MemoryManager
from oh_memos.memories.textual.tree_text_memory.retrieve.bm25_util import EnhancedBM25
from oh_memos.memories.textual.tree_text_memory.retrieve.retrieve_utils import FastTokenizer
from oh_memos.reranker.base import BaseReranker


if TYPE_CHECKING:
    from oh_memos.embedders.factory import OllamaEmbedder
    from oh_memos.graph_dbs.factory import Neo4jGraphDB
    from oh_memos.llms.factory import AzureLLM, OllamaLLM, OpenAILLM


logger = get_logger(__name__)


class SimpleTreeTextMemory(TreeTextMemory):
    """General textual memory implementation for storing and retrieving memories."""

    def __init__(
        self,
        llm: BaseLLM,
        embedder: BaseEmbedder,
        mem_reader: BaseMemReader,
        graph_db: BaseGraphDB,
        reranker: BaseReranker,
        memory_manager: MemoryManager,
        config: TreeTextMemoryConfig,
        internet_retriever: None = None,
        is_reorganize: bool = False,
        tokenizer: FastTokenizer | None = None,
        include_embedding: bool = False,
    ):
        """Initialize memory with the given configuration."""
        self.config: TreeTextMemoryConfig = config
        self.mode = self.config.mode
        logger.info(f"Tree mode is {self.mode}")

        self.extractor_llm: OpenAILLM | OllamaLLM | AzureLLM = llm
        self.dispatcher_llm: OpenAILLM | OllamaLLM | AzureLLM = llm
        self.embedder: OllamaEmbedder = embedder
        self.graph_store: Neo4jGraphDB = graph_db
        self.search_strategy = config.search_strategy
        self.bm25_retriever = (
            EnhancedBM25()
            if self.search_strategy and self.search_strategy.get("bm25", False)
            else None
        )
        self.tokenizer = tokenizer
        self.reranker = reranker
        self.memory_manager: MemoryManager = memory_manager
        # Create internet retriever if configured
        self.internet_retriever = None
        if config.internet_retriever is not None:
            self.internet_retriever = internet_retriever
            logger.info(
                f"Internet retriever initialized with backend: {config.internet_retriever.backend}"
            )
        else:
            logger.info("No internet retriever configured")
        self.include_embedding = include_embedding
