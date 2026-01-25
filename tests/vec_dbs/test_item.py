import uuid

import pytest

from pydantic import ValidationError

from memos.vec_dbs.item import VecDBItem


def test_item_creation():
    id = str(uuid.uuid4())
    item = VecDBItem(id=id, vector=[0.1, 0.2, 0.3], payload={"foo": "bar"})
    assert item.id == id
    assert item.vector == [0.1, 0.2, 0.3]
    assert item.payload == {"foo": "bar"}
    assert item.score is None


def test_item_with_score():
    item = VecDBItem(vector=[1.0], payload={}, score=0.99)
    assert item.score == 0.99


def test_item_validation():
    with pytest.raises(ValidationError):
        VecDBItem(id=None, vector=[0.1], payload={})
    with pytest.raises(ValidationError):
        VecDBItem(id="id", vector=None, payload={})


def test_item_from_dict():
    id = str(uuid.uuid4())
    d = {"id": id, "vector": [1, 2], "payload": {"a": 1}, "score": 0.5}
    item = VecDBItem.from_dict(d)
    assert item.id == id
    assert item.vector == [1, 2]
    assert item.payload == {"a": 1}
    assert item.score == 0.5
