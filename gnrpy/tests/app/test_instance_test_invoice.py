import pytest
from common import checkInstance

INSTANCE_NAME = "test_invoice"

app = checkInstance(INSTANCE_NAME)
if not app:
    pytest.skip(f"Instance {INSTANCE_NAME} not available", allow_module_level=True)

class TestInvoiceInstance:
    """App tests using the test_invoice instance"""

    def setup_method(self):
        self.app = app

    def test_app_loaded(self):
        assert self.app is not None

    def test_instance_name(self):
        assert self.app.instanceName == INSTANCE_NAME

    def test_packages_loaded(self):
        packages = list(self.app.packages.keys())
        assert len(packages) > 0
        assert 'invc' in packages
