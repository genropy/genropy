"""HEIC attachments keep their original file while offering a JPEG preview and PDF export."""

from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest
from PIL import Image
from PyPDF2 import PdfReader

from core.common import BaseGnrTest
from gnr.app.gnrapp import GnrApp
from gnr.core.gnrlang import gnrImport
from gnr.web.gnrdummysite import GnrDummySite

pillow_heif = pytest.importorskip('pillow_heif')
ROOT = Path(__file__).resolve().parents[3]
endpoint = gnrImport(str(ROOT / 'projects/gnrcore/packages/sys/webpages/ep_table.py'), avoidDup=True)
externalcall = gnrImport(str(ROOT / 'resources/common/gnrcomponents/externalcall.py'), avoidDup=True)


class EndpointPage(endpoint.GnrCustomWebPage, externalcall.EndpointPermission):
    pass


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
        self.page.response = SimpleNamespace()
        self.page.getPublicMethod = lambda *args: None
        self.page.setInClientRecord = lambda *args, **kwargs: None
        template = ROOT / 'projects/gnrcore/packages/sys/resources/ep_table/download_file_tpl.html'
        self.page.getResourceContent = lambda **kwargs: template.read_text()

    def attach(self, name, data):
        node = self.site.storageNode('home:', self.parent['id'], name)
        with node.open('wb') as out:
            out.write(data)
        return self.table.addAttachment(maintable_id=self.parent['id'], origin_filepath=node,
                                        copyFile=False)

    @pytest.mark.parametrize('extension,legacy', [('HEIC', False), ('heif', True)])
    def test_preview_download_and_pdf(self, extension, legacy, monkeypatch):
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
        monkeypatch.setattr(self.site.register, 'page', lambda *a, **kw: None, raising=False)
        assert self.page.rootPage(*args, **params) == endpoint.AUTH_FORBIDDEN
        monkeypatch.setattr(self.site.register, 'page',
                            lambda *a, **kw: dict(user='tester', register_item_id='test'))
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

    def test_invalid_heif_offers_original(self, monkeypatch):
        rec = self.attach('broken.heic', b'unsupported content')
        monkeypatch.setattr(self.site.register, 'page',
                            lambda *a, **kw: dict(user='tester', register_item_id='test'), raising=False)
        args = ('adm', 'htmltemplate_atc', rec['id'], 'get', 'filepath')
        assert 'force_download=True' in self.page.rootPage(*args, heif_preview=True)
        assert self.page.rootPage(*args, force_download=True) == b'unsupported content'
