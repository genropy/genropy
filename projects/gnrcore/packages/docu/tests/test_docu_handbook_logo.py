"""Tests for the handbook logo of the docu preferences.

The logo shown by every published handbook is uploaded from the application
preferences. It belongs to the `documentation` storage, where every other docu
asset already lives - the attachments of the pages, their images, the preview
image of the handbook - so that pointing that storage at a bucket of its own
takes the logo along instead of leaving it on the instance home.

Where it is stored decides how the build can link it: the sphinx conf gets the
public url of the file when its service publishes it on a public base of its
own, and the instance-served url otherwise, which is also what the logos
uploaded on the instance home before the move keep answering.
"""
import os
import shutil
import tempfile

import pytest

from gnr.core.gnrlang import gnrImport
from gnr.web.gnrwebstruct import GnrDomSrc_dojo_11

from core.common import BaseGnrAppTest
from sitestub import (INSTANCE_HOST, PUBLIC_HOST, PrivateBucketLocalService,
                      SigningLocalService, StorageSiteStub)

LOGO_PATH = 'img/docu_logo.png'
LEGACY_LOGO_PATH = 'documentation/img/docu_logo.png'


class _PermissiveApp:
    """The application as the structure builder asks it about permissions."""

    def checkResourcePermission(self, *args, **kwargs):
        return True

    def allowedByPreference(self, *args, **kwargs):
        return True


class _StructPage:
    """The page a preference pane is built on, outside a request."""

    filepath = __file__
    application = _PermissiveApp()
    maintable = None
    pageOptions = {}

    def __init__(self):
        self._register_nodeId = {}

    def checkTablePermission(self, **kwargs):
        return True

    def getPreference(self, *args, **kwargs):
        return None


class TestDocuHandbookLogo(BaseGnrAppTest):

    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.db = cls.app.db
        cls.db.model.check(applyChanges=True)
        cls.doctbl = cls.db.table('docu.documentation')
        cls.dirs = {name: tempfile.mkdtemp(prefix='gnr_docu_%s_' % name)
                    for name in ('documentation', 'home')}

    @classmethod
    def teardown_class(cls):
        for folder in getattr(cls, 'dirs', {}).values():
            shutil.rmtree(folder, ignore_errors=True)
        super().teardown_class()

    # ------------------------------------------------------------------
    # where the preference uploads it
    # ------------------------------------------------------------------

    def _handbooksThemeStruct(self):
        module_path = os.path.join(self.app.packages['docu'].packageFolder,
                                   'resources', 'preference.py')
        module = gnrImport(module_path, avoidDup=True)
        root = GnrDomSrc_dojo_11.makeRoot(_StructPage())
        module.AppPref().handbooksTheme(root.child('div', childname='pane'))
        return root

    def _logoNode(self):
        found = []

        def collect(struct_node):
            if struct_node.attr.get('tag') == 'img':
                found.append(struct_node)
            if hasattr(struct_node.value, 'nodes'):
                for child in struct_node.value.nodes:
                    collect(child)

        for node in self._handbooksThemeStruct().nodes:
            collect(node)
        assert len(found) == 1
        return found[0]

    def test_the_logo_is_uploaded_on_the_documentation_storage(self):
        """Every other docu asset already lives there: a documentation storage
        mounted on a bucket of its own must take the logo along, instead of
        stranding it on the instance home."""
        attributes = self._logoNode().attr
        assert attributes['upload_folder'] == 'documentation:img'
        assert attributes['upload_filename'] == 'docu_logo.png'

    # ------------------------------------------------------------------
    # how the build links it
    # ------------------------------------------------------------------

    def _batch(self, documentation_service=None):
        """Export batch whose site keeps the documentation storage in the given
        flavour, with the logo already uploaded on it and on the instance home."""
        pytest.importorskip('sphinx')
        pytest.importorskip('boto3')
        module_path = os.path.join(self.app.packages['docu'].packageFolder,
                                   'resources', 'tables', 'handbook', 'action',
                                   'export_to_sphinx.py')
        module = gnrImport(module_path, avoidDup=True)
        site = StorageSiteStub(self.app, 'docu', dict(home=self.dirs['home']))
        site.addService('documentation', self.dirs['documentation'],
                        documentation_service)
        #the storage urls the instance writes into the preference are host-relative,
        #the form externalUrl and the public-url gate both expect
        site.external_host = ''
        self.app.site = site
        for fullpath in ('documentation:%s' % LOGO_PATH,
                         'home:%s' % LEGACY_LOGO_PATH):
            with site.storageNode(fullpath).open('wb') as logo_file:
                logo_file.write(b'PNG-logo')
        batch = module.Main(page=site.currentPage, resource_table=self.db.table('docu.handbook'))
        batch.doctable = self.doctbl
        batch.mediaUrlsDict = {}
        return batch

    def _storedLogo(self, service, path):
        """The preference value the img widget writes: the internal url of the
        uploaded file."""
        return self.app.site.storageNode('%s:%s' % (service, path)).internal_url()

    def test_a_public_documentation_storage_is_linked_by_its_public_url(self):
        """A documentation storage publishing on a public base of its own carries
        the logo with the rest of the handbook: the build links it there, with no
        signature to expire and no instance to depend on."""
        batch = self._batch(SigningLocalService)
        logo_url = batch.logoUrl(self._storedLogo('documentation', LOGO_PATH))
        assert logo_url.startswith(PUBLIC_HOST)
        assert 'Signature' not in logo_url

    def test_a_plain_documentation_storage_is_served_by_the_instance(self):
        """Nothing declares the default storage publicly readable, so the logo
        keeps the instance-served url it has always had."""
        batch = self._batch()
        logo_url = batch.logoUrl(self._storedLogo('documentation', LOGO_PATH))
        assert logo_url == '%s/_storage/documentation/%s' % (INSTANCE_HOST, LOGO_PATH)

    def test_a_private_bucket_is_served_by_the_instance(self):
        """A storage answering public_url() with a bucket url it was never told is
        public would publish a 403: the logo stays instance-served."""
        batch = self._batch(PrivateBucketLocalService)
        logo_url = batch.logoUrl(self._storedLogo('documentation', LOGO_PATH))
        assert logo_url == '%s/_storage/documentation/%s' % (INSTANCE_HOST, LOGO_PATH)

    def test_a_logo_already_on_the_instance_home_keeps_working(self):
        """The preference holds the url of the file, not a name resolved against
        the upload folder: a logo uploaded before the move is still resolved where
        it was left, so the change needs no migration."""
        batch = self._batch()
        logo_url = batch.logoUrl(self._storedLogo('home', LEGACY_LOGO_PATH))
        assert logo_url == '%s/_storage/home/%s' % (INSTANCE_HOST, LEGACY_LOGO_PATH)
