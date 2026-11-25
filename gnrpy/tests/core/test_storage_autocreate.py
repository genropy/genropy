import contextlib
import io

import pytest

from gnr.lib.services.storage import StorageNode


class RecordingService:
    is_versioned = False

    def __init__(self):
        self.autocreated = []

    def expandpath(self, path):
        return path

    def autocreate(self, *args, **kwargs):
        self.autocreated.append(args)

    def open(self, *args, **kwargs):
        return io.BytesIO()

    @contextlib.contextmanager
    def local_path(self, *args, **kwargs):
        yield '/tmp/x'


def _node():
    return StorageNode(service=RecordingService(), path='docs/a/file.pdf')


@pytest.mark.parametrize('mode', ['r', 'rb'])
def test_open_for_reading_does_not_autocreate(mode):
    """On S3 autocreate costs a HEAD and a LIST before every read (#1960)."""
    node = _node()
    node.open(mode=mode)
    assert node.service.autocreated == []


@pytest.mark.parametrize('mode', ['w', 'wb', 'a', 'ab', 'x', 'r+', 'rb+'])
def test_open_for_writing_autocreates(mode):
    node = _node()
    node.open(mode=mode)
    assert node.service.autocreated == [('docs/a/file.pdf',)]


def test_local_path_for_reading_does_not_autocreate():
    node = _node()
    with node.local_path(mode='r'):
        pass
    assert node.service.autocreated == []


@pytest.mark.parametrize('mode', [None, 'w', 'rw'])
def test_local_path_without_mode_or_for_writing_autocreates(mode):
    node = _node()
    with node.local_path(mode=mode):
        pass
    assert node.service.autocreated == [('docs/a/file.pdf',)]
