import os
import pytest
from gnr.app.gnrapp import GnrApp


INSTANCE_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..', 'instances', 'test_invoice_pg')
)

@pytest.fixture(scope='session')
def app():
    """Load the test_invoice_pg GnrApp instance (PostgreSQL)."""
    if not os.path.isdir(INSTANCE_PATH):
        pytest.skip('test_invoice_pg instance not found')
    return GnrApp(INSTANCE_PATH)

@pytest.fixture(scope='session')
def db(app):
    """Return the db object from the app."""
    return app.db
