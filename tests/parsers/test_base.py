from memos.parsers.base import BaseParser
from tests.utils import check_module_base_class


def test_base_parser_class():
    check_module_base_class(BaseParser)
