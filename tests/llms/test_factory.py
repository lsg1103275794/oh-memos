from memos.llms.factory import LLMFactory
from tests.utils import check_module_factory_class


def test_llm_factory():
    check_module_factory_class(cls=LLMFactory)
