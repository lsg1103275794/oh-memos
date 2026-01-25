from memos.chunkers.factory import ChunkerFactory
from tests.utils import check_module_factory_class


def test_chunker_factory():
    check_module_factory_class(cls=ChunkerFactory)
