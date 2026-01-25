from memos.llms.base import BaseLLM
from tests.utils import check_module_base_class


def test_base_llm_class():
    check_module_base_class(BaseLLM)
