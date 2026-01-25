from memos.mem_chat.factory import MemChatFactory
from tests.utils import check_module_factory_class


def test_mem_chat_factory():
    check_module_factory_class(cls=MemChatFactory)
