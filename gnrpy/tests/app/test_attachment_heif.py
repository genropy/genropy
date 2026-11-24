"""HEIC attachments keep their original file while offering a JPEG preview and PDF export."""

import sys
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest
from PIL import Image
from PyPDF2 import PdfReader, PdfWriter

from core.common import BaseGnrTest
from gnr.app.gnrapp import GnrApp
from gnr.core.gnrlang import gnrImport
from gnr.web.gnrdummysite import GnrDummySite

ROOT = Path(__file__).resolve().parents[3]
endpoint = gnrImport(str(ROOT / 'projects/gnrcore/packages/sys/webpages/ep_table.py'), avoidDup=True)


class EndpointPage(endpoint.GnrCustomWebPage):
    userTags = ''


class TestHeifAttachments(BaseGnrTest):
    @classmethod
    def setup_class(cls):
        super().setup_class()
        bootstrap = GnrApp(cls.test_instance_name)
        bootstrap.db.model.check(applyChanges=True)
        bootstrap.db.commit()
        bootstrap.db.closeConnection()
        cls.site = GnrDummySite(cls.test_instance_name)
        cls.site.config.setAttr('wsgi', external_host='http://localhost')
        cls.db = cls.site.gnrapp.db
        cls.table = cls.db.table('adm.htmltemplate_atc')

    @classmethod
    def teardown_class(cls):
        cls.db.closeConnection()
        super().teardown_class()

    def setup_method(self):
        master = self.db.table('adm.htmltemplate')
        self.parent = master.newrecord(name='Receipt')
        master.insert(self.parent)
        self.page = EndpointPage()
        self.page.db = self.db
        self.page.site = self.site
        self.page.application = self.site.gnrapp
        self.page.connection = SimpleNamespace(loggedUser=None)
        self.page.response = self.page._response = SimpleNamespace(status_code=200)
        self.page.getPublicMethod = lambda *args: None
        self.page.setInClientRecord = lambda *args, **kwargs: None
        resources = ROOT / 'projects/gnrcore/packages/sys/resources'
        self.page.getResourceContent = lambda resource, ext: (resources / f'{resource}.{ext}').read_text()
        self.page._ = lambda value: value

    def attach(self, name, data):
        node = self.site.storageNode('home:', self.parent['id'], name)
        with node.open('wb') as out:
            out.write(data)
        return self.table.addAttachment(maintable_id=self.parent['id'], origin_filepath=node,
                                        copyFile=False)

    @pytest.mark.parametrize('extension,legacy', [('HEIC', False), ('heif', True)])
    def test_preview_download_and_pdf(self, extension, legacy):
        pillow_heif = pytest.importorskip('pillow_heif')
        buf = BytesIO()
        pillow_heif.from_pillow(Image.new('RGB', (96, 64), 'red')).save(buf)
        data = buf.getvalue()
        rec = self.attach(f'receipt.{extension}', data)
        if legacy:
            with self.table.recordToUpdate(rec['id']) as stored:
                stored['filepath'] = stored['filepath'].replace('home:', 'home/', 1)
        url = self.table.record(rec['id']).output('dict')['fileurl']
        params = {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}
        assert 'heif_preview' in params
        args = ('adm', 'htmltemplate_atc', rec['id'], 'get', 'filepath')
        assert 'Log in' in self.page.rootPage(*args, **params)
        assert self.page._response.status_code == 403
        self.page.connection.loggedUser = 'tester'
        preview = self.page.rootPage(*args, **params)
        assert self.page.response.content_type == 'image/jpeg'
        with Image.open(BytesIO(preview)) as decoded:
            assert decoded.format == 'JPEG'
            assert decoded.size == (96, 64)
        assert self.page.rootPage(*args, force_download=True, **params) == data
        original_url = self.table.pyColumn_full_external_url(self.table.record(rec['id']).output('dict'), None)
        assert 'heif_preview' not in original_url
        if legacy:
            assert '/_vol/home/' in original_url

        buf = BytesIO()
        Image.new('RGB', (64, 96), 'blue').save(buf, 'JPEG')
        self.attach('receipt.jpg', buf.getvalue())
        out = self.table.getAttachmentsPdf(self.parent['id'], output_path='home:receipts.pdf')
        with out.open('rb') as pdf:
            pages = PdfReader(pdf).pages
            assert len(pages) == 2
            assert len({tuple(p.mediabox) for p in pages}) == 2

    @pytest.mark.parametrize('interactive', [False, True])
    def test_export_without_heif_decoder(self, monkeypatch, caplog, interactive):
        monkeypatch.setitem(sys.modules, 'pillow_heif', None)
        self.attach('scan.HEIC', b'')
        pdf = BytesIO()
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=144)
        writer.write(pdf)
        self.attach('document.pdf', pdf.getvalue())
        jpeg = BytesIO()
        Image.new('RGB', (100, 50)).save(jpeg, 'JPEG')
        self.attach('photo.jpg', jpeg.getvalue())
        self.attach('second.heif', b'')

        notifications = []
        if interactive:
            page = self.site.dummyPage
            page.locale = 'it'
            monkeypatch.setattr(page, 'page_id', 'test')
            monkeypatch.setattr(page, 'clientPublish', lambda topic, **kw: notifications.append((topic, kw)))
            monkeypatch.setattr(self.site, 'currentPage', page)
        out = self.table.getAttachmentsPdf(self.parent['id'], output_path='home:partial.pdf')
        with out.open('rb') as exported:
            pages = PdfReader(exported).pages
            assert len(pages) == 2
            assert {(p.mediabox.width, p.mediabox.height) for p in pages} == {(72, 144), (72, 36)}
        warnings = [r.getMessage() for r in caplog.records if 'pillow-heif' in r.getMessage()]
        assert len(warnings) == 1
        assert 'omitted' in warnings[0]
        if interactive:
            assert notifications == [('floating_message', dict(message='Gli allegati HEIC/HEIF sono stati esclusi dal PDF. Puoi scaricare gli originali separatamente.',
                                                               messageType='warning'))]

    def test_invalid_heif_offers_original(self):
        rec = self.attach('broken.heic', b'unsupported content')
        self.page.connection.loggedUser = 'tester'
        args = ('adm', 'htmltemplate_atc', rec['id'], 'get', 'filepath')
        assert 'force_download=True' in self.page.rootPage(*args, heif_preview=True)
        assert self.page.rootPage(*args, force_download=True) == b'unsupported content'
