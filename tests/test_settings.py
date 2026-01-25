from memos.settings import (
    DEBUG,
    MEMOS_DIR,
)


def test_memos_dir():
    """Test if the MEMOS_DIR is created correctly."""
    assert MEMOS_DIR.is_dir()
    assert MEMOS_DIR.name == ".memos"


def test_debug():
    """Test if the DEBUG setting is set correctly."""
    assert DEBUG in [True, False]
