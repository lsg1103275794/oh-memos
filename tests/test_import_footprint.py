"""Importing the package must not load ML runtimes the API never calls.

torch/transformers serve only KV-cache activation memory and local HF models, and
sklearn only the optional TF-IDF rerank and KMeans partitioning. Every backend in
the default deployment is a remote API, yet these libraries used to load with
``import oh_memos`` and cost each API process hundreds of MB. OpenBLAS (bundled
with numpy/scipy) also committed a work buffer per CPU thread at import.

Each probe runs in a fresh interpreter: pytest has already imported these
libraries itself (see conftest.py), so ``sys.modules`` here would prove nothing.
"""

import json
import os
import subprocess
import sys

from pathlib import Path

import pytest


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
UNUSED_RUNTIMES = ("torch", "transformers", "sklearn", "scipy")
# Package logging and exit handlers may also write to stdout, so tag the result line.
RESULT_PREFIX = "IMPORT_FOOTPRINT "
PROBE = f"""
import json, os, sys
import oh_memos
loaded = [name for name in {UNUSED_RUNTIMES!r} if name in sys.modules]
from threadpoolctl import threadpool_info
pools = [p["num_threads"] for p in threadpool_info() if p.get("internal_api") == "openblas"]
print({RESULT_PREFIX!r} + json.dumps({{
    "loaded": loaded,
    "openblas_threads": os.environ.get("OPENBLAS_NUM_THREADS"),
    "openblas_pool_threads": pools,
}}))
"""


def import_in_fresh_interpreter(**env_overrides: str) -> dict:
    env = {key: value for key, value in os.environ.items() if key != "OPENBLAS_NUM_THREADS"}
    env.update(env_overrides)
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(SRC_DIR), env.get("PYTHONPATH")]))
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        [sys.executable, "-c", PROBE],
        env=env,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    assert result.returncode == 0, result.stderr[-3000:]
    lines = [line for line in result.stdout.splitlines() if line.startswith(RESULT_PREFIX)]
    assert lines, result.stdout[-3000:]
    return json.loads(lines[-1].removeprefix(RESULT_PREFIX))


@pytest.fixture(scope="module")
def default_import() -> dict:
    return import_in_fresh_interpreter()


def test_import_leaves_unused_ml_runtimes_unloaded(default_import):
    assert default_import["loaded"] == []


def test_import_caps_openblas_threads_by_default(default_import):
    assert default_import["openblas_threads"] == "1"
    # OpenBLAS sizes its pool when numpy loads, so this also fails if numpy is
    # ever imported before the cap is set.
    assert all(threads == 1 for threads in default_import["openblas_pool_threads"])


def test_import_keeps_explicit_openblas_setting():
    assert import_in_fresh_interpreter(OPENBLAS_NUM_THREADS="4")["openblas_threads"] == "4"
