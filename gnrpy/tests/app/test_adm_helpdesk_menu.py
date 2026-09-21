"""Guards for the helpdesk slot of the adm frame index.

``fi_slotbar_helpdesk`` runs while ``prepareBottom_std`` composes the frame
index toolbar, so anything it raises reaches ``rpc_main`` and no page is
served at all. The failure only appears once a group has at least one help
document linked, which is why the fixture below links one for real instead of
faking the query result.

The resource is loaded by path: ``projects/`` is not importable as a package.
"""

import importlib.util
import pathlib

import pytest

from core.common import BaseGnrTest

from gnr.web.gnrwebstruct import GnrDomSrc_dojo_11

FRAMEINDEX = (pathlib.Path(__file__).parents[3] / 'projects' / 'gnrcore'
              / 'packages' / 'adm' / 'resources' / 'frameindex.py')

GROUP_CODE = 'HLPDSK'
DOC_TITLE = 'Operator handbook'
DOC_URL = 'https://example.org/handbook'
DOCUMENTATION_CB = 'genro.openBrowserTab("https://example.org/app");'


def _load_frameindex():
    spec = importlib.util.spec_from_file_location('adm_frameindex', FRAMEINDEX)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


frameindex = _load_frameindex()


def setup_module(module):
    BaseGnrTest.setup_class()


def teardown_module(module):
    BaseGnrTest.teardown_class()


class _AppStub(object):
    def checkResourcePermission(self, *args, **kwargs):
        return True

    def allowedByPreference(self, *args, **kwargs):
        return True


class _AvatarStub(object):
    def __init__(self, group_code):
        self.group_code = group_code


class _HelpdeskPage(frameindex.FrameIndex):
    filepath = str(FRAMEINDEX)
    application = _AppStub()
    maintable = None
    pageOptions = {}

    def __init__(self, db, group_code=None, documentationcb=None):
        self._register_nodeId = {}
        self.db = db
        self.avatar = _AvatarStub(group_code)
        self._documentationcb = documentationcb

    def checkTablePermission(self, **kwargs):
        return True

    def getPreference(self, *args, **kwargs):
        return None

    def helpdesk_documentation(self):
        return self._documentationcb


def _only_child(src):
    nodes = list(src)
    assert len(nodes) == 1
    return nodes[0]


def _helpdesk_slot(page):
    root = GnrDomSrc_dojo_11.makeRoot(page)
    page.fi_slotbar_helpdesk(root)
    return root


@pytest.fixture(scope='module')
def helpdesk_db(db_sqlite):
    db_sqlite.table('adm.group').insert(
        dict(code=GROUP_CODE, description='Helpdesk test group'))
    helpdoc = dict(title=DOC_TITLE, url=DOC_URL)
    db_sqlite.table('adm.helpdoc').insert(helpdoc)
    db_sqlite.table('adm.group_helpdoc').insert(
        dict(group_code=GROUP_CODE, helpdoc_id=helpdoc['id']))
    db_sqlite.commit()
    return db_sqlite


def test_group_documentation_carries_title_and_url(helpdesk_db):
    page = _HelpdeskPage(helpdesk_db, group_code=GROUP_CODE)
    rows = page.helpdesk_userGroupDocumentation()
    assert len(rows) == 1
    assert rows[0]['title'] == DOC_TITLE
    assert rows[0]['url'] == DOC_URL


def test_group_documentation_without_group(helpdesk_db):
    page = _HelpdeskPage(helpdesk_db)
    assert page.helpdesk_userGroupDocumentation() is None


def test_group_document_becomes_a_submenu_line(helpdesk_db):
    page = _HelpdeskPage(helpdesk_db, group_code=GROUP_CODE)
    menudiv = _only_child(_helpdesk_slot(page))
    assert menudiv.attr['tag'] == 'MenuDiv'
    documentation = _only_child(menudiv.value)
    assert documentation.attr['code'] == 'documentation'
    submenu = _only_child(documentation.value)
    assert submenu.attr['action'] == 'genro.openBrowserTab($1.url);'
    line = _only_child(submenu.value)
    assert line.attr['label'] == DOC_TITLE
    assert line.attr['url'] == DOC_URL


def test_open_documentation_is_an_action(helpdesk_db):
    page = _HelpdeskPage(helpdesk_db, documentationcb=DOCUMENTATION_CB)
    menudiv = _only_child(_helpdesk_slot(page))
    documentation = _only_child(menudiv.value)
    assert documentation.attr['action'] == DOCUMENTATION_CB
    assert 'documentationcb' not in documentation.attr


def test_helpdesk_slot_stays_empty_without_documentation(helpdesk_db):
    page = _HelpdeskPage(helpdesk_db)
    assert len(list(_helpdesk_slot(page))) == 0
