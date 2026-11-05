"""Shared test bootstrap.

The import chain ``oh_memos -> configs -> mem_reader -> transformers -> torch``
makes every contract test fail at collection time on hosts where the torch
Windows DLLs cannot initialize (WinError 1114, a broken local install — not a
code defect). The memory write/relation contracts under test never touch torch
or transformers themselves, so when a real import is impossible we substitute
minimal stubs. Hosts with a working torch keep the real libraries untouched.
"""

from __future__ import annotations

import os
import shutil
import sys
import time
from pathlib import Path

from unittest.mock import MagicMock

import pytest


def _stub_if_unimportable(module_name: str) -> None:
    if module_name in sys.modules:
        return
    try:
        __import__(module_name)
    except Exception:
        sys.modules[module_name] = MagicMock(name=module_name)


_stub_if_unimportable("torch")
# transformers.DynamicCache is imported by oh_memos.memories.activation.item;
# a MagicMock module satisfies it without pulling the real (torch-backed) lib.
_stub_if_unimportable("transformers")


# Test temp files live under <repo>/runtime/scratch/pytest/ (.agents/contracts/common/artifacts.md).
# Each session gets runtime/scratch/pytest/<pid>/. A green session removes it on exit; a failing or
# interrupted one keeps it for inspection, and a later session sweeps leftovers older than a day.
# An explicit --basetemp belongs to the caller: never redirected or removed.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRATCH_ROOT = PROJECT_ROOT / 'runtime' / 'scratch' / 'pytest'
STALE_SECONDS = 86400
_OWNED = pytest.StashKey[Path]()


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    if config.option.basetemp is not None:
        return
    SCRATCH_ROOT.mkdir(parents=True, exist_ok=True)
    for old in SCRATCH_ROOT.iterdir():
        try:
            if old.is_dir() and time.time() - old.stat().st_mtime > STALE_SECONDS:
                shutil.rmtree(old, ignore_errors=True)
        except OSError:
            pass
    basetemp = SCRATCH_ROOT / str(os.getpid())
    config.option.basetemp = str(basetemp)
    config.stash[_OWNED] = basetemp


@pytest.hookimpl(trylast=True)
def pytest_unconfigure(config):
    # Runs after every plugin's sessionfinish, so nothing can still be using tmp_path.
    basetemp = config.stash.get(_OWNED, None)
    if basetemp is None or getattr(config, '_scratch_failed', True):
        return
    shutil.rmtree(basetemp, ignore_errors=True)
    if basetemp.exists():
        print(f'\n[scratch] could not remove {basetemp} (a file is still open?); delete it by hand')
    try:
        SCRATCH_ROOT.rmdir()  # only succeeds when no other session left anything behind
    except OSError:
        pass


def pytest_sessionfinish(session, exitstatus):
    session.config._scratch_failed = exitstatus != 0
