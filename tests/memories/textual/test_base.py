from memos.memories.textual.base import BaseTextMemory
from tests.utils import check_module_base_class


def test_base_memory_class():
    check_module_base_class(BaseTextMemory)
