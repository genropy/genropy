"""Import bridge for the helpers the smoke suite reuses from gnrpy/tests.

`BaseGnrDaemonTest` (gnrpy/tests/web/webcommon.py) and `WSGITestClient`
(gnrpy/tests/web/utils.py) live in a tree that is not part of the installed
`gnr` package, so pytest cannot import them by package name. Both
`gnrpy/tests` and `gnrpy/tests/web` go on `sys.path`: the second one is
required because `webcommon` itself does `from utils import WSGITestClient`,
which only resolves with the `web` folder on the path.
"""
import os
import sys

GENROPY_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), *[os.pardir] * 5))
GNRPY_TESTS = os.path.join(GENROPY_ROOT, 'gnrpy', 'tests')

for _helper_path in (GNRPY_TESTS, os.path.join(GNRPY_TESTS, 'web')):
    if _helper_path not in sys.path:
        sys.path.insert(0, _helper_path)
