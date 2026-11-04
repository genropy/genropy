from pathlib import Path

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
