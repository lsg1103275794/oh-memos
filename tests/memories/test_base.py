from memos.memories.base import BaseMemory
from tests.utils import check_module_base_class


def test_base_memory_class():
    check_module_base_class(BaseMemory)
