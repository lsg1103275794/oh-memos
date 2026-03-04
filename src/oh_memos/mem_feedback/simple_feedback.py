from oh_memos import log
from oh_memos.embedders.factory import OllamaEmbedder
from oh_memos.graph_dbs.factory import PolarDBGraphDB
from oh_memos.llms.factory import AzureLLM, OllamaLLM, OpenAILLM
from oh_memos.mem_feedback.feedback import MemFeedback
from oh_memos.mem_reader.simple_struct import SimpleStructMemReader
from oh_memos.memories.textual.simple_preference import SimplePreferenceTextMemory
from oh_memos.memories.textual.tree_text_memory.organize.manager import MemoryManager
from oh_memos.memories.textual.tree_text_memory.retrieve.retrieve_utils import StopwordManager
from oh_memos.memories.textual.tree_text_memory.retrieve.searcher import Searcher
from oh_memos.reranker.base import BaseReranker


logger = log.get_logger(__name__)


class SimpleMemFeedback(MemFeedback):
    def __init__(
        self,
        llm: OpenAILLM | OllamaLLM | AzureLLM,
        embedder: OllamaEmbedder,
        graph_store: PolarDBGraphDB,
        memory_manager: MemoryManager,
        mem_reader: SimpleStructMemReader,
        searcher: Searcher,
        reranker: BaseReranker,
        pref_mem: SimplePreferenceTextMemory,
        pref_feedback: bool = False,
    ):
        self.llm = llm
        self.embedder = embedder
        self.graph_store = graph_store
        self.memory_manager = memory_manager
        self.mem_reader = mem_reader
        self.searcher = searcher
        self.stopword_manager = StopwordManager
        self.pref_mem = pref_mem
        self.reranker = reranker
        self.DB_IDX_READY = False
        self.pref_feedback = pref_feedback
