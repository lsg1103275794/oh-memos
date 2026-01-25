from memos.vec_dbs.factory import VecDBFactory
from tests.utils import check_module_factory_class


def test_vec_db_factory():
    check_module_factory_class(cls=VecDBFactory)
