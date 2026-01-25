from memos.vec_dbs.base import BaseVecDB
from tests.utils import check_module_base_class


def test_base_vec_db_class():
    check_module_base_class(BaseVecDB)
