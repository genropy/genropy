"""Top-level test configuration.

Provides a session-scoped cleanup fixture that removes any leftover
tmp_* directories from tests/core/ at the end of the test session.
These directories are created by BaseGnrTest.setup_class() and should
be removed by each test's teardown_class() or its atexit backstop, but
this fixture is a final guarantee that they never accumulate in the
source tree regardless of how the test suite is invoked.
"""

import os
import shutil

import pytest


@pytest.fixture(scope='session', autouse=True)
def _cleanup_core_tmp_dirs():
    yield
    core_dir = os.path.join(os.path.dirname(__file__), 'core')
    if not os.path.isdir(core_dir):
        return
    for entry in os.listdir(core_dir):
        if entry.startswith('tmp_'):
            shutil.rmtree(os.path.join(core_dir, entry), ignore_errors=True)
