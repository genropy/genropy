"""The download flag on the serving path and on the signed url (#1346).

``internal_url()`` marks a download with ``_download``, which comes back as a
query kwarg, while every service reads ``download`` when it serves: the local
half checks both spellings on a real file served by a real site.

The S3 half signs the url instead of serving it: the disposition is asserted on
the parameters the service hands to ``generate_presigned_url``, with the boto
client stood in because the defect is in the parameters, not in the transport.
"""

from core.common import BaseGnrTest

from gnr.app.gnrapp import GnrApp
from gnr.core.gnrlang import getUuid
from gnr.web.gnrdummysite import GnrDummySite

from test_s3_public_url import FakeParent, S3Service


class ResponseRecorder:
    """A WSGI start_response keeping what the responder answered"""

    def __init__(self):
        self.status = None
        self.headers = None

    def __call__(self, status, headers, exc_info=None):
        self.status = status
        self.headers = headers

    def header(self, name):
        return dict(self.headers or []).get(name)


class TestLocalServeDownload(BaseGnrTest):

    @classmethod
    def setup_class(cls):
        super().setup_class()
        app = GnrApp(cls.test_instance_name)
        app.db.model.check(applyChanges=True)
        app.db.commit()
        cls.site = GnrDummySite(cls.test_instance_name, site_name=cls.test_instance_name)

    def setup_method(self):
        self.basename = '%s.txt' % getUuid()
        self.node = self.site.storageNode('home:storage_download_test/%s' % self.basename)
        with self.node.open(mode='w') as served_file:
            served_file.write('served content')

    def teardown_method(self):
        self.node.delete()

    def _serve(self, **kwargs):
        recorder = ResponseRecorder()
        body = self.node.serve({}, recorder, **kwargs)
        assert b''.join(body) == b'served content'
        return recorder

    def test_download_serves_an_attachment(self):
        recorder = self._serve(download=True)
        assert recorder.status == '200 OK'
        assert recorder.header('Content-Disposition') == \
            'attachment; filename=%s' % self.basename

    def test_underscore_download_serves_an_attachment(self):
        """``?_download=True`` is what internal_url() puts in its own url"""
        recorder = self._serve(_download='True')
        assert recorder.status == '200 OK'
        assert recorder.header('Content-Disposition') == \
            'attachment; filename=%s' % self.basename

    def test_plain_serve_stays_inline(self):
        recorder = self._serve()
        assert recorder.status == '200 OK'
        assert recorder.header('Content-Disposition') is None


class RecordingS3Client:

    def __init__(self):
        self.params = None

    def generate_presigned_url(self, operation, Params=None, ExpiresIn=None):
        self.operation = operation
        self.params = Params
        self.expires_in = ExpiresIn
        return 'https://signed.example.com/%s' % Params['Key']


class StubbedClientS3Service(S3Service):

    @property
    def _client(self):
        return self.recording_client


class TestS3UrlDisposition:

    def setup_method(self):
        self.service = StubbedClientS3Service(parent=FakeParent(), bucket='mybucket',
                                              region_name='eu-west-1')
        self.service.recording_client = RecordingS3Client()

    def _disposition(self, **kwargs):
        self.service.url('some/file.txt', **kwargs)
        return self.service.recording_client.params['ResponseContentDisposition']

    def test_download_signs_an_attachment(self):
        """btcprint calls url(nocache=True, download=True)"""
        assert self._disposition(download=True) == 'attachment; filename=file.txt'

    def test_underscore_download_signs_an_attachment(self):
        assert self._disposition(_download=True) == 'attachment; filename=file.txt'

    def test_default_is_inline(self):
        assert self._disposition() == 'inline'

    def test_explicit_content_disposition_is_kept(self):
        disposition = 'attachment; filename=renamed.txt'
        assert self._disposition(_content_disposition=disposition) == disposition
