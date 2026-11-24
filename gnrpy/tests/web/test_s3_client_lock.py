import importlib.util
import os
import threading
import time
from datetime import datetime, timedelta

from gnr.core.gnrbag import Bag

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


class FakeApp:
    def __init__(self):
        self.config = Bag()
        self.config['packages'] = Bag()


class FakeParent:
    def __init__(self):
        self.gnrapp = FakeApp()
        self._local_mode = False


class SlowSession:
    """Counts sessions and clients; client creation is slow, to widen the race window."""
    created = []

    def __init__(self, **kwargs):
        SlowSession.created.append('session')

    def client(self, *args, **kwargs):
        time.sleep(0.05)
        SlowSession.created.append('client')
        return object()


def _make_service(expired=True):
    service = aws_s3.Service(parent=FakeParent(), bucket='mybucket', region_name='eu-west-1',
                             aws_access_key_id='AKIDTEST', aws_secret_access_key='secret')
    service._boto_client = service._boto_session = object()
    age = timedelta(seconds=300 if expired else 0)
    service._boto_client_ts = service._boto_session_ts = datetime.now() - age
    return service


def test_expired_client_is_rebuilt_once_by_concurrent_threads(monkeypatch):
    """Threads reading an expired client used to rebuild it each, concurrently,
    on a boto3 session that is not thread-safe (#1963)."""
    monkeypatch.setattr(aws_s3.boto3, 'Session', SlowSession)
    SlowSession.created = []
    service = _make_service()
    clients = []
    barrier = threading.Barrier(8)

    def read_client():
        barrier.wait()
        clients.append(service._client)

    threads = [threading.Thread(target=read_client) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert SlowSession.created == ['session', 'client']
    assert len({id(c) for c in clients}) == 1


def test_slow_rebuild_does_not_block_another_service(monkeypatch):
    """Each service guards only its own session and client: a slow rebuild
    (e.g. credentials fetched over the network) must not stall other buckets."""
    rebuilding = threading.Event()

    class BlockingSession(SlowSession):
        def client(self, *args, **kwargs):
            rebuilding.set()
            time.sleep(0.5)
            return object()

    monkeypatch.setattr(aws_s3.boto3, 'Session', BlockingSession)
    slow, fresh = _make_service(), _make_service(expired=False)
    thread = threading.Thread(target=lambda: slow._client)
    thread.start()
    rebuilding.wait()
    start = time.monotonic()
    fresh._client
    elapsed = time.monotonic() - start
    thread.join()
    assert elapsed < 0.1
