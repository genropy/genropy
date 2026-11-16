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
        return txt[2:] if txt.startswith('!!') else txt


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


class VirusProbeException(GnrException):
    caption = 'Upload of %(filename)s failed: virus detected'
    feedback = dict(title='!!Error', level='error', sound='Basso')


def test_an_exception_with_feedback_answers_with_its_parameters_and_its_message():
    rpc, result = upload(VirusProbeException(filename='report.pdf'))
    envelope = Bag(result)
    assert envelope['error'] == 'gnrexception'
    assert envelope['result'] == dict(title='Error', level='error', sound='Basso',
                                      message='Upload of report.pdf failed: virus detected')


def test_an_exception_without_feedback_answers_with_its_message_alone():
    rpc, result = upload(GnrException('Upload of empty.pdf failed: the file is empty'))
    assert isinstance(Bag(result)['result'], str)


def test_an_unexpected_error_still_propagates():
    try:
        upload(ValueError('boom'))
    except ValueError:
        return
    raise AssertionError('a non GnrException must not be swallowed')
