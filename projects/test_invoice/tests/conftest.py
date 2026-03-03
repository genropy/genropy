import os
import pytest
from gnr.app.gnrapp import GnrApp


INSTANCES_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), '..', 'instances')
)

INSTANCE_MAP = {
    'sqlite': os.path.join(INSTANCES_DIR, 'test_invoice'),
    'pg': os.path.join(INSTANCES_DIR, 'test_invoice_pg'),
}


def _make_app(instance_name):
    path = INSTANCE_MAP[instance_name]
    if not os.path.isdir(path):
        pytest.skip(f'{instance_name} instance not found at {path}')
    return GnrApp(path)


@pytest.fixture(scope='session', params=['sqlite', 'pg'])
def app(request):
    """Load the test_invoice GnrApp instance (parametrized: sqlite / pg)."""
    return _make_app(request.param)


@pytest.fixture(scope='session')
def db(app):
    """Return the db object from the app."""
    return app.db
