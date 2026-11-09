import importlib.util
import io
import os

import pytest

from gnr.core.gnrbag import Bag
from gnr.core.gnrlang import GnrException
from gnr.lib.services.storage import StorageNode

# The aws_s3 Service lives under projects/gnrcore/ which is not on the
# default test sys.path: it is loaded from the file system.
_s3_module_path = os.path.normpath(os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir, os.pardir,
    'projects', 'gnrcore', 'packages', 'sys', 'resources',
    'services', 'storage', 'aws_s3.py',
))


def _load_s3_module():
    spec = importlib.util.spec_from_file_location('aws_s3', _s3_module_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


aws_s3 = _load_s3_module()

WRITE_MODES = ['w', 'wb', 'a', 'ab', 'x', 'xb', 'r+', 'rb+', 'w+b']


class FakeApp:
    def __init__(self, secondary=False):
        self.config = Bag()
        self.config['packages'] = Bag()
        if secondary:
            self.config['packages'].setItem('gnrcore:sys', None, secondary=True)


class FakeParent:
    def __init__(self, local_mode=False, secondary=False):
        self.gnrapp = FakeApp(secondary=secondary)
        self._local_mode = local_mode


class FakeSmartOpen:
    """Stands in for smart_open, the only way the service reaches the bucket."""

    def __init__(self):
        self.calls = []

    def __call__(self, uri, transport_params=None, **kwargs):
        self.calls.append((uri, kwargs['mode']))
        return io.BytesIO()


@pytest.fixture
def smart_open(monkeypatch):
    fake = FakeSmartOpen()
    monkeypatch.setattr(aws_s3, 'so_open', fake)
    return fake


def _make_service(local_mode=False, secondary=False, **kwargs):
    parent = FakeParent(local_mode=local_mode, secondary=secondary)
    service = aws_s3.Service(parent=parent, bucket='mybucket',
                             region_name='eu-west-1', aws_access_key_id='AKIDTEST',
                             aws_secret_access_key='secret', **kwargs)
    service.service_name = 'app'
    return service


@pytest.mark.parametrize('mode', WRITE_MODES)
def test_write_on_readonly_service_raises_before_s3(smart_open, mode):
    """A write used to be turned into a read of a key that does not exist yet:
    uploading an attachment failed with NoSuchKey (issue #1368)."""
    service = _make_service(readonly=True)
    with pytest.raises(GnrException) as excinfo:
        service.open('docs', 'file.pdf', mode=mode)
    message = str(excinfo.value)
    assert 'app is read-only' in message
    assert 's3://mybucket/docs/file.pdf' in message
    assert smart_open.calls == []
    assert not hasattr(service, '_boto_client')


@pytest.mark.parametrize('machine', [{'local_mode': True}, {'secondary': True}])
def test_write_without_write_in_local_raises(smart_open, machine):
    service = _make_service(**machine)
    assert service.readonly
    with pytest.raises(GnrException):
        service.open('docs', 'file.pdf', mode='wb')
    assert smart_open.calls == []


def test_storage_node_write_on_readonly_skips_autocreate(smart_open):
    service = _make_service(readonly=True)
    node = StorageNode(parent=service.parent, service=service, path='docs/file.pdf')
    with pytest.raises(GnrException, match='app is read-only'):
        node.open('wb')
    assert smart_open.calls == []
    assert not hasattr(service, '_boto_client')


@pytest.mark.parametrize('mode', ['rb', 'r'])
def test_read_on_readonly_service_reaches_s3(smart_open, mode):
    service = _make_service(readonly=True)
    service.open('docs', 'file.pdf', mode=mode)
    assert smart_open.calls == [('s3://mybucket/docs/file.pdf', mode)]


def test_write_in_local_keeps_the_write_mode(smart_open):
    service = _make_service(local_mode=True, write_in_local=True)
    service.open('docs', 'file.pdf', mode='wb')
    assert smart_open.calls == [('s3://mybucket/docs/file.pdf', 'wb')]
