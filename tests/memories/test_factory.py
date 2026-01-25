from memos.memories.factory import MemoryFactory
from tests.utils import check_module_factory_class


def test_memory_factory():
    check_module_factory_class(cls=MemoryFactory)
