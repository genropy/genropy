from pathlib import Path
from types import SimpleNamespace

import pytest

from gnr.core.gnrbag import Bag
from gnr.core.gnrlang import gnrImport
from gnr.web.gnrwebstruct import GnrDomSrc, GnrDomSrc_dojo_11


@pytest.fixture
def panel_page():
    saved = GnrDomSrc._external_methods.copy()
    resource = Path(__file__).resolve().parents[3] / 'resources/common/gnrcomponents/grouplet/grouplet.py'
    component = gnrImport(str(resource))

    class Application:
        def allowedByPreference(self, **kwargs):
            return True

        def checkResourcePermission(self, *args, **kwargs):
            return True

    class Page(component.GroupletHandler):
        filepath = __file__
        application = Application()
        maintable = None
        pageOptions = {}
        inlineDoc = False
        package = SimpleNamespace(name='test')

        def __init__(self):
            self._register_nodeId = {}

    yield Page()
    GnrDomSrc._external_methods.clear()
    GnrDomSrc._external_methods.update(saved)


@pytest.mark.parametrize('use_form', [False, True])
@pytest.mark.parametrize('topic', [None, 'visit'])
def test_panel_remote_parameters_reach_the_selected_widget(panel_page, use_form, topic):
    menu = Bag()
    menu.setItem('first', None, resource='visit/section', grouplet_caption='First',
                 mandatory='value', locationpath='first')
    menu.setItem('second', None, resource='visit/section', grouplet_caption='Second',
                 mandatory='value', locationpath='second')
    root = GnrDomSrc_dojo_11.makeRoot(panel_page)
    panel_page.gr_groupletPanel(root, useForm=use_form, topic=topic, value='^.record',
                               menuCallback=lambda **kwargs: menu, startResource=True)
    nodes = []
    root.walk(lambda node: nodes.append(node) if node.attr.get('tag', '').lower()
              in ('grouplet', 'groupletform') else None)
    assert len(nodes) == 1
    attrs = nodes[0].attr
    assert attrs['tag'].lower() == ('groupletform' if use_form else 'grouplet')
    prefix = 'grouplet_' if use_form else ''
    assert attrs[f'{prefix}remote_mandatory_enforced'] == '#ANCHOR.mandatory_enforced'
    if topic:
        assert attrs[f'{prefix}remote_topic'] == topic
    else:
        assert attrs[f'{prefix}remote__reloader'] == '^#ANCHOR.selected_fullpath'
    assert menu['first?mandatory_path'] == 'first'
    assert menu['second?mandatory_path'] == 'second'


def tree_panel_doc_buttons(page):
    menu = Bag()
    menu.setItem('first', None, resource='visit/section', grouplet_caption='First')
    root = GnrDomSrc_dojo_11.makeRoot(page)
    page.gr_groupletPanel(root, value='^.record', frameCode='visit_panel',
                          menuCallback=lambda **kwargs: menu, startResource=True)
    found = []
    root.walk(lambda node: found.append(node) if 'helperbutton' in (node.attr.get('_class') or '') else None)
    return found


@pytest.mark.parametrize('flag', [True, False])
def test_the_tree_panel_title_has_a_large_doc_button_with_the_flag(panel_page, flag):
    panel_page.inlineDoc = flag
    buttons = tree_panel_doc_buttons(panel_page)
    if not flag:
        assert buttons == []
        return
    assert len(buttons) == 1
    attrs = buttons[0].attr
    assert attrs['nodeId'] == 'visit_panel_doc'
    assert not attrs.get('docAddress')
    assert 'helperbutton_large' in attrs['_class'].split()
    assert 'doc_icon' in attrs['_class'].split()


@pytest.mark.parametrize('doc, expected', [
    (None, 'grouplet:test.visit:visit/section'),
    ('grouplet:test:shared_notes', 'grouplet:test:shared_notes'),
    (False, False),
])
def test_the_menu_leaves_carry_their_doc_address(panel_page, doc, expected):
    panel_page.inlineDoc = True
    panel_page._get_grouplet_info = lambda node, table=None: dict(caption='Section', doc=doc)
    resources = Bag()
    resources.setItem('section', None)
    menu = Bag()
    panel_page._buildGroupletMenu(menu, resources, table='test.visit', parent_path='visit')
    assert menu['section?docAddress'] == expected


def test_the_menu_leaves_have_no_doc_address_without_the_flag(panel_page):
    panel_page._get_grouplet_info = lambda node, table=None: dict(caption='Section')
    resources = Bag()
    resources.setItem('section', None)
    menu = Bag()
    panel_page._buildGroupletMenu(menu, resources, table='test.visit')
    assert 'docAddress' not in menu.getNode('section').attr


def test_the_doc_button_without_an_address_waits_for_one(panel_page):
    root = GnrDomSrc_dojo_11.makeRoot(panel_page)
    root.docHelpButton(None, size='large')
    button = root.getNode('#0')
    assert button.attr['_class'].split() == ['helperbutton', 'iconbox', 'innericonbox', 'doc_icon',
                                             'helperbutton_large']
    assert 'if(this.attr.docAddress)' in button.attr['onCreated']
