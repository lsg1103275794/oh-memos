from memos.parsers.factory import ParserFactory
from tests.utils import check_module_factory_class


def test_parser_factory():
    check_module_factory_class(ParserFactory)
