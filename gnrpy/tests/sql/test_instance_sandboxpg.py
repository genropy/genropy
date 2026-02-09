import pytest
from .common import checkInstance

INSTANCE_NAME = "sandboxpg"

app = checkInstance(INSTANCE_NAME)
if not app:
    pytest.skip(f"Instance {INSTANCE_NAME} not available", allow_module_level=True)

class TestSandboxpg:
    """SQL tests using the sandboxpg instance database"""

    def setup_method(self):
        self.db = app.db

    def test_connection(self):
        assert self.db is not None

    def test_packages_loaded(self):
        packages = list(self.db.packages.keys())
        assert len(packages) > 0
