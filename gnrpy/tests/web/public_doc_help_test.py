"""The "?" of the published manual and of the customer's notes in the public
components (resources/common/public.py): only with the inlinedoc flag."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from gnr.core.gnrlang import gnrImport
from gnr.web.gnrwebstruct import GnrDomSrc, GnrDomSrc_dojo_11


@pytest.fixture
def public_page():
    saved = GnrDomSrc._external_methods.copy()
    resource = Path(__file__).resolve().parents[3] / 'resources/common/public.py'
    component = gnrImport(str(resource))

    class Application:
        def allowedByPreference(self, **kwargs):
            return True

        def checkResourcePermission(self, *args, **kwargs):
            return True

    class Page(component.PublicBase):
        filepath = __file__
        application = Application()
        package = SimpleNamespace(name='test')
        pagename = 'agenda'
        inlineDoc = True
        _call_kwargs = {}

        def __init__(self):
            self._register_nodeId = {}

        def _(self, txt):
            return txt

    yield Page()
    GnrDomSrc._external_methods.clear()
    GnrDomSrc._external_methods.update(saved)


def doc_addresses(root):
    found = []
    root.walk(lambda node: found.append(node.attr['docAddress']) if 'docAddress' in node.attr else None)
    return found


def top_bar_slots(root):
    found = []
    root.walk(lambda node: found.append(node.attr['slots']) if 'slots' in node.attr else None)
    return found[0]


@pytest.mark.parametrize('flag', [True, False])
def test_the_help_of_the_page_and_of_its_groups_needs_the_flag(public_page, flag):
    public_page.inlineDoc = flag
    root = GnrDomSrc_dojo_11.makeRoot(public_page)
    public_page.public_frameTopBar(root.contentPane())
    assert ('pageHelp' in top_bar_slots(root).split(',')) is flag
    root = GnrDomSrc_dojo_11.makeRoot(public_page)
    box = root.div()
    public_page.public_roundedGroup(box, title='Day', helpcode='day')
    public_page.public_roundedGroupFrame(box, title='Week', frameCode='week', helpcode='week')
    assert doc_addresses(root) == (['page:test/agenda:day', 'page:test/agenda:week'] if flag else [])
