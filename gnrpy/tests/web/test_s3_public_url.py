import importlib.util
import os

import pytest

# boto3 is an optional dependency (genropy[s3]) and the aws_s3 module imports
# it at module level, so the whole file is skipped when it is not installed.
pytest.importorskip('boto3')

from gnr.core.gnrbag import Bag  # noqa: E402
from gnr.lib.services.storage import StorageNode, StorageService  # noqa: E402

# The aws_s3 Service lives under projects/gnrcore/ which is not on the
# default test sys.path.  We load it directly from the file system so the
# test can run without requiring a full GenroPy site setup.
_s3_module_path = os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir, os.pardir,
    'projects', 'gnrcore', 'packages', 'sys', 'resources',
    'services', 'storage', 'aws_s3.py',
)
_s3_module_path = os.path.normpath(_s3_module_path)


def _get_s3_service_class():
    """Import Service from the aws_s3 module."""
    spec = importlib.util.spec_from_file_location('aws_s3', _s3_module_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.Service


S3Service = _get_s3_service_class()


class FakeApp:
    def __init__(self):
        self.config = Bag()
        self.config['packages'] = Bag()


class FakeParent:
    def __init__(self):
        self.gnrapp = FakeApp()


def _make_service(**kwargs):
    kwargs.setdefault('bucket', 'mybucket')
    kwargs.setdefault('region_name', 'eu-west-1')
    return S3Service(parent=FakeParent(), **kwargs)


class TestS3PublicUrl:
    """Tests for issue #988: plain, non-expiring public urls."""

    def test_default_aws_endpoint(self):
        service = _make_service()
        assert service.public_url('some/file.txt') == \
            'https://s3.eu-west-1.amazonaws.com/mybucket/some/file.txt'

    def test_base_path_is_included(self):
        service = _make_service(base_path='media')
        assert service.public_url('some/file.txt') == \
            'https://s3.eu-west-1.amazonaws.com/mybucket/media/some/file.txt'

    def test_custom_endpoint(self):
        """A custom endpoint (e.g. SeaweedFS/MinIO gateway) replaces the AWS one."""
        service = _make_service(custom_endpoint=True,
                                endpoint_url='http://seaweed.local:8333')
        assert service.public_url('some/file.txt') == \
            'http://seaweed.local:8333/mybucket/some/file.txt'

    def test_custom_endpoint_trailing_slash(self):
        service = _make_service(custom_endpoint=True,
                                endpoint_url='http://seaweed.local:8333/')
        assert service.public_url('some/file.txt') == \
            'http://seaweed.local:8333/mybucket/some/file.txt'

    def test_endpoint_url_ignored_without_custom_endpoint_flag(self):
        service = _make_service(custom_endpoint=False,
                                endpoint_url='http://seaweed.local:8333')
        assert service.public_url('some/file.txt') == \
            'https://s3.eu-west-1.amazonaws.com/mybucket/some/file.txt'

    def test_public_base_url_overrides_endpoint(self):
        """public_base_url replaces both endpoint and bucket (CDN/custom domain)."""
        service = _make_service(public_base_url='https://media.example.com')
        assert service.public_url('some/file.txt') == \
            'https://media.example.com/some/file.txt'

    def test_public_base_url_trailing_slash(self):
        service = _make_service(public_base_url='https://media.example.com/')
        assert service.public_url('some/file.txt') == \
            'https://media.example.com/some/file.txt'

    def test_public_base_url_keeps_base_path(self):
        service = _make_service(public_base_url='https://media.example.com',
                                base_path='media')
        assert service.public_url('some/file.txt') == \
            'https://media.example.com/media/some/file.txt'

    def test_missing_region_falls_back_to_global_endpoint(self):
        """Without region_name (e.g. credentials from env) use the global endpoint."""
        service = _make_service(region_name=None)
        assert service.public_url('some/file.txt') == \
            'https://s3.amazonaws.com/mybucket/some/file.txt'

    def test_url_is_stable_across_calls(self):
        service = _make_service()
        first = service.public_url('some/file.txt')
        second = service.public_url('some/file.txt')
        assert first == second


class TestStorageNodePublicUrl:

    def test_node_delegates_to_service(self):
        service = _make_service()
        node = StorageNode(parent=None, path='some/file.txt', service=service)
        assert node.public_url() == \
            'https://s3.eu-west-1.amazonaws.com/mybucket/some/file.txt'


class TestBaseServicePublicUrl:

    def test_base_service_falls_back_to_url(self):
        """Services without signed urls return the plain url() unchanged."""

        class PlainService(StorageService):
            def __init__(self):
                pass

            def url(self, *args, **kwargs):
                return 'https://example.com/%s' % '/'.join(args)

        service = PlainService()
        assert service.public_url('some/file.txt') == \
            'https://example.com/some/file.txt'
