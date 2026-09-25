import hashlib
import importlib.util
import io
import os

from gnr.lib.services.storage import StorageService

_s3_module_path = os.path.normpath(os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir, os.pardir,
    'projects', 'gnrcore', 'packages', 'sys', 'resources',
    'services', 'storage', 'aws_s3.py',
))

CONTENT = b'<?xml version="1.0"?><FatturaElettronica/>' * 3000
CONTENT_MD5 = hashlib.md5(CONTENT).hexdigest()
NEW_CONTENT = b'<?xml version="1.0"?><FatturaElettronica versione="FPR12"/>' * 3000
NEW_CONTENT_MD5 = hashlib.md5(NEW_CONTENT).hexdigest()


def _s3_service_class():
    spec = importlib.util.spec_from_file_location('aws_s3', _s3_module_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.Service


class ContentOnlyService(StorageService):
    """A storage service that can only read one blob: exercises the base md5hash."""

    def __init__(self, content):
        self.content = content
        self.opened = 0

    def open(self, *args, **kwargs):
        self.opened += 1
        return io.BytesIO(self.content)


def _s3_service(etag, content=CONTENT):
    service = object.__new__(_s3_service_class())
    service.etag = etag
    service.content = content
    service.opened = 0

    def open_content(*args, **kwargs):
        service.opened += 1
        return io.BytesIO(service.content)

    service._head_object = lambda *args: {'ETag': f'"{service.etag}"'} if service.etag else False
    service.open = open_content
    return service


def test_base_md5hash_streams_the_content():
    service = ContentOnlyService(CONTENT)
    assert service.md5hash('any', 'path') == CONTENT_MD5
    assert service.opened == 1


def test_s3_md5hash_uses_the_etag_when_it_is_an_md5():
    service = _s3_service(CONTENT_MD5)
    service.open = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('must not read'))
    assert service.md5hash('file.xml') == CONTENT_MD5


def test_s3_md5hash_reads_the_content_on_multipart_etag():
    assert _s3_service(CONTENT_MD5 + '-1').md5hash('file.xml') == CONTENT_MD5


def test_s3_md5hash_reads_a_multipart_object_once_per_etag():
    service = _s3_service(CONTENT_MD5 + '-1')
    assert service.md5hash('file.xml') == CONTENT_MD5
    assert service.md5hash('file.xml') == CONTENT_MD5
    assert service.opened == 1


def test_s3_md5hash_reads_again_when_the_etag_changes():
    service = _s3_service(CONTENT_MD5 + '-1')
    assert service.md5hash('file.xml') == CONTENT_MD5
    service.etag = NEW_CONTENT_MD5 + '-1'
    service.content = NEW_CONTENT
    assert service.md5hash('file.xml') == NEW_CONTENT_MD5
    assert service.opened == 2


def test_s3_md5hash_does_not_share_an_etag_across_paths():
    service = _s3_service(CONTENT_MD5 + '-1')
    assert service.md5hash('a.xml') == CONTENT_MD5
    service.content = NEW_CONTENT
    assert service.md5hash('b.xml') == NEW_CONTENT_MD5
    assert service.opened == 2


def test_s3_md5hash_is_none_for_a_missing_object():
    assert _s3_service(None).md5hash('missing.xml') is None
