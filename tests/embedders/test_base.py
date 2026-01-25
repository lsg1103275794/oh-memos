from memos.embedders.base import BaseEmbedder
from tests.utils import check_module_base_class


def test_base_embedder_class():
    check_module_base_class(BaseEmbedder)
