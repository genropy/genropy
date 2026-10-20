import types

from gnr.web.cli import gnrtaskworker


def test_start_old_passes_code_to_worker(monkeypatch):
    created = {}

    class FakeWorker:
        def __init__(self, sitename, interval=None, code=None):
            created.update(sitename=sitename, interval=interval, code=code)

        def start(self):
            pass

    monkeypatch.setattr(gnrtaskworker.gnrtask, "GnrTaskWorker", FakeWorker)
    gnrtaskworker.start_old(types.SimpleNamespace(sitename="mysite", interval=5, code="pdf"))
    assert created == dict(sitename="mysite", interval=5, code="pdf")
