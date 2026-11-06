"""Guard the test scratch contract (.agents/contracts/common/artifacts.md).

Place next to the conftest that carries the scratch hooks. It copies that real conftest into
child pytest sessions rooted in this test's own tmp_path (a throwaway project), and checks:
green sessions delete their temp dir, failing ones keep it, leftovers older than a day are
swept without touching fresh sessions, and an explicit --basetemp is left alone. The child
projects live under this test's own tmp_path, which the conftest places in
runtime/scratch/pytest/<pid>/: a green run removes them, and if the run is killed they stay
there until a later session sweeps them.
"""
import os
import re
import shutil
import subprocess
import sys
import textwrap
import time
from pathlib import Path

CONFTEST = Path(__file__).with_name('conftest.py')
PRINT_SESSION = "print('SESSION=' + str(tmp_path.parent))"


def _child_project(tmp_path) -> Path:
    """A throwaway project: <tmp>/proj/tests/conftest.py rooted at <tmp>/proj."""
    project = tmp_path / 'proj'
    (project / 'tests').mkdir(parents=True)
    source = CONFTEST.read_text(encoding='utf-8')
    assert re.search(r'^PROJECT_ROOT = ', source, re.M), 'conftest must define PROJECT_ROOT'
    # A function replacement keeps Windows backslashes literal (a string one would read \r, \a ...).
    anchored = f"PROJECT_ROOT = Path({str(project)!r})"
    source = re.sub(r'^PROJECT_ROOT = .*$', lambda _: anchored, source, count=1, flags=re.M)
    (project / 'tests' / 'conftest.py').write_text(source, encoding='utf-8')
    return project


def _run_pytest(project, body, *args):
    (project / 'tests' / 'test_probe.py').write_text(textwrap.dedent(body), encoding='utf-8')
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}
    return subprocess.run([sys.executable, '-m', 'pytest', '-q', '-s', '-p', 'no:cacheprovider', 'tests', *args],
                          cwd=project, env=env, capture_output=True, text=True, timeout=120)


def _child_session(project, result) -> Path:
    line = next(line for line in result.stdout.splitlines() if line.startswith('SESSION='))
    path = Path(line.removeprefix('SESSION=')).resolve()
    assert path.parent == (project / 'runtime' / 'scratch' / 'pytest').resolve() and path.name.isdigit(), path
    return path


def test_passing_session_removes_its_basetemp(tmp_path):
    project = _child_project(tmp_path)
    result = _run_pytest(project, f'''
        def test_writes(tmp_path):
            (tmp_path / 'probe.txt').write_text('x')
            {PRINT_SESSION}
        ''')
    assert result.returncode == 0, result.stdout + result.stderr
    assert not _child_session(project, result).exists(), 'a green session leaves nothing behind'
    assert not (project / 'runtime' / 'scratch' / 'pytest').exists(), 'nor an empty pytest/ folder'


def test_failing_session_keeps_its_basetemp_for_inspection(tmp_path):
    project = _child_project(tmp_path)
    result = _run_pytest(project, f'''
        def test_fails(tmp_path):
            (tmp_path / 'evidence.txt').write_text('x')
            {PRINT_SESSION}
            assert False
        ''')
    assert result.returncode == 1, result.stdout + result.stderr
    assert list(_child_session(project, result).rglob('evidence.txt')), 'failure evidence is kept'


def test_stale_session_dirs_are_swept_but_fresh_ones_kept(tmp_path):
    project = _child_project(tmp_path)
    root = project / 'runtime' / 'scratch' / 'pytest'
    stale, fresh = root / 'stale-session', root / 'fresh-session'
    for path in (stale, fresh):
        path.mkdir(parents=True)
        (path / 'x.txt').write_text('x')
    old = time.time() - 2 * 86400
    os.utime(stale, (old, old))
    result = _run_pytest(project, '''
        def test_noop():
            pass
        ''')
    assert result.returncode == 0, result.stdout + result.stderr
    assert not stale.exists(), 'leftovers older than a day are swept'
    assert fresh.exists(), 'a possibly running session is never touched'


def test_explicit_basetemp_is_respected_and_kept(tmp_path):
    project = _child_project(tmp_path)
    target = tmp_path / 'explicit-basetemp'
    result = _run_pytest(project, '''
        def test_writes(tmp_path):
            (tmp_path / 'probe.txt').write_text('x')
        ''', f'--basetemp={target}')
    assert result.returncode == 0, result.stdout + result.stderr
    assert list(target.rglob('probe.txt')), 'an explicit --basetemp belongs to the caller'
    assert not (project / 'runtime').exists(), 'and the scratch root is not even created'
