from memos.mem_reader.base import BaseMemReader
from tests.utils import check_module_base_class


def test_base_mem_reader():
    """Test that BaseMemReader is a proper abstract base class."""
    check_module_base_class(BaseMemReader)
