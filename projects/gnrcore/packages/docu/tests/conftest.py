"""Bridge to the shared gnrpy test infrastructure.

Package tests live under packages/<pkg>/tests but reuse the test
environment builders (BaseGnrAppTest & co.) shipped in gnrpy/tests of
the same checkout. That gnrpy is also put first on sys.path, so the
tests exercise this checkout's code even when another genropy checkout
is the installed one.
"""
import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), *['..'] * 5))
_GNRPY_DIR = os.path.join(_REPO_ROOT, 'gnrpy')

for _path in (os.path.join(_GNRPY_DIR, 'tests'), _GNRPY_DIR):
    if _path not in sys.path:
        sys.path.insert(0, _path)
