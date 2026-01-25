from memos.embedders.factory import EmbedderFactory
from tests.utils import check_module_factory_class


def test_embedder_factory():
    check_module_factory_class(EmbedderFactory)
