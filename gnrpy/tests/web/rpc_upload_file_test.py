from gnr.core.gnrbag import Bag
from gnr.core.gnrlang import GnrException
from gnr.web.gnrwebpage_proxy.rpc import GnrWebRpc


class FakeSite:
    def __init__(self, error):
        self.error = error

    def raiseIfDeveloper(self):
        pass

    def uploadFile(self, **kwargs):
        raise self.error


class FakePage:
    domSrcFactory = type('DomSrc', (), {})

    def __init__(self, site):
        self.site = site
        self.response = type('Response', (), {})()
        self.catalog = None

    def isLocalizer(self):
        return False

    def collectClientDatachanges(self):
        return None

    def localize(self, txt, **kwargs):
        return txt


def upload(error):
    rpc = GnrWebRpc.__new__(GnrWebRpc)
    rpc.page = FakePage(FakeSite(error))
    return rpc, rpc.rpc_upload_file(file_handle=object(), uploadPath='site:upload_probe')


def test_a_refused_upload_answers_with_a_gnrexception_envelope():
    rpc, result = upload(GnrException('Upload of empty.pdf failed: the file is empty'))
    envelope = Bag(result)
    assert envelope['error'] == 'gnrexception'
    assert 'empty.pdf' in envelope['result']
    assert rpc.page.response.content_type == 'text/xml'


def test_an_unexpected_error_still_propagates():
    try:
        upload(ValueError('boom'))
    except ValueError:
        return
    raise AssertionError('a non GnrException must not be swallowed')
