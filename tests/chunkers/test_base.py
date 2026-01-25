from memos.chunkers.base import BaseChunker
from tests.utils import check_module_base_class


def test_base_chunker_class():
    check_module_base_class(BaseChunker)
