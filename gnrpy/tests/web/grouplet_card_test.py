from pathlib import Path

import pytest

from gnr.core.gnrlang import gnrImport
from gnr.web.gnrwebstruct import GnrDomSrc, GnrDomSrc_dojo_11


class StructError(Exception):
    pass


@pytest.fixture
def card_page():
    saved = GnrDomSrc._external_methods.copy()
    resource = Path(__file__).resolve().parents[3] / 'resources/common/gnrcomponents/grouplet/grouplet.py'
    component = gnrImport(str(resource))

    class Application:
        def allowedByPreference(self, **kwargs):
            return True

        def checkResourcePermission(self, *args, **kwargs):
            return True

    class Page(component.GroupletCardHandler, component.GroupletGridHandler, component.GroupletHandler):
        filepath = __file__
        application = Application()
        maintable = None
        pageOptions = {}
        resource_info = ({}, None)

        def __init__(self):
            self._register_nodeId = {}

        def _(self, txt):
            return txt

        def exception(self, kind, msg=None, **kwargs):
            return StructError(msg)

        def _gr_resourceInfo(self, resource=None, table=None, grouplets_root=None):
            return self.resource_info

        def resolveResourceUri(self, fpath, add_mtime=False, pkg=None):
            return '/_rsrc/' + Path(fpath).name

    yield Page()
    GnrDomSrc._external_methods.clear()
    GnrDomSrc._external_methods.update(saved)


def nodes_by_tag(root, tag):
    found = []
    root.walk(lambda node: found.append(node) if node.attr.get('tag', '').lower() == tag else None)
    return found


def host_kw(root):
    """The kw the card's JS host is built with"""
    return [n for n in nodes_by_tag(root, 'datacontroller') if 'GroupletCardHost' in n.attr.get('script', '')][0].attr['kw']


def test_a_card_alone_is_a_titled_box_returning_its_body(card_page):
    root = GnrDomSrc_dojo_11.makeRoot(card_page)
    body = card_page.gr_groupletCard(root, datapath='.contact', title='!!Contact', nodeId='c1')
    card = root.getNode('#0')
    assert card.attr['_class'] == 'grouplet_card grouplet_card--box grouplet_card--chrome-top'
    assert card.attr['datapath'] == '.contact'
    assert body.parentNode.attr['_class'] == 'grouplet_card_body'
    kw = host_kw(root)
    assert kw['title'] == '!!Contact'
    assert kw['collapsible'] is False, 'not collapsible unless asked'
    assert kw['delitem'] is False
    assert kw['collapsedPath'] is None
    assert card.value.getNode('#0').attr['path'] == '#WORKSPACE.collapsed'


def test_chrome_side_is_top_left_or_right(card_page):
    root = GnrDomSrc_dojo_11.makeRoot(card_page)
    with pytest.raises(StructError):
        card_page.gr_groupletCard(root, chromeSide='bottom')


def test_the_profile_is_the_resource_card_then_the_caller(card_page, tmp_path):
    (tmp_path / 'address_doc.html').write_text('<p>$city</p><img src="zones.svg"><img src="https://x/y.png">')
    card_page.resource_info = (dict(template='$city', card=dict(collapsible='closed', tools='title,doc',
                                                                delitem=True, doc='file:address_doc.html')),
                               str(tmp_path / 'address.py'))
    root = GnrDomSrc_dojo_11.makeRoot(card_page)
    card_page.gr_groupletCard(root, resource='address', tools='title,menu', datapath='.address')
    kw = host_kw(root)
    assert kw['tools'] == 'title,menu', 'the caller wins'
    assert kw['collapsible'] is True
    assert kw['delitem'] is True
    assert kw['template'] == '$city', 'the resource template is the title of last resort'
    assert kw['doc']['template'] == '<p>$city</p><img src="/_rsrc/zones.svg"><img src="https://x/y.png">'
    assert root.getNode('#0').value.getNode('#0').attr['path'] == '#WORKSPACE.collapsed'
    grouplet = nodes_by_tag(root, 'grouplet')[0]
    assert grouplet.attr['resource'] == 'address'
    assert grouplet.attr['value'] == '^.'


def test_a_bound_state_is_watched_where_the_caller_placed_the_card(card_page):
    root = GnrDomSrc_dojo_11.makeRoot(card_page)
    pane = root.div()
    card_page.gr_groupletCard(pane, datapath='.contact', collapsible=True, nodeId='c1',
                              collapsed='^.state.collapsed', checkbox='^.state.checked')
    kw = host_kw(root)
    assert (kw['collapsedPath'], kw['checkboxPath']) == ('.state.collapsed', '.state.checked')
    watchers = [n for n in pane if n.attr.get('tag', '').lower() == 'datacontroller']
    assert {n.attr.get('collapsed') or n.attr.get('checked') for n in watchers} == \
        {'^.state.collapsed', '^.state.checked'}, 'on the caller pane, not inside the card'


def test_a_grid_takes_its_profile_from_the_resource_card(card_page):
    card_page.resource_info = (dict(card=dict(chromeSide='left', delitem=False, tools='title')), None)
    root = GnrDomSrc_dojo_11.makeRoot(card_page)
    card_page.gr_groupletGrid(root, storepath='.rows', resource='row', nodeId='g1', card_tools='title,menu')
    controller = [n for n in nodes_by_tag(root, 'datacontroller')
                  if 'GroupletGridController' in n.attr.get('script', '')][0]
    assert controller.attr['chromeSide'] == 'left'
    assert controller.attr['delitem'] is False
    assert controller.attr['card']['tools'] == 'title,menu', 'card_* kwargs win'
    plain = GnrDomSrc_dojo_11.makeRoot(card_page)
    card_page.resource_info = ({}, None)
    card_page.gr_groupletGrid(plain, storepath='.rows', resource='row', nodeId='g2')
    controller = [n for n in nodes_by_tag(plain, 'datacontroller')
                  if 'GroupletGridController' in n.attr.get('script', '')][0]
    assert (controller.attr.get('chromeSide'), controller.attr['delitem']) == (None, True), 'defaults unchanged'


def test_use_form_edits_the_grouplet_in_a_form_of_its_own(card_page):
    root = GnrDomSrc_dojo_11.makeRoot(card_page)
    pane = root.div()
    card_page.gr_groupletCard(pane, datapath='.shipping', resource='address', useForm=True,
                              nodeId='c1', form_autoSave=500)
    form = nodes_by_tag(root, 'groupletform')[0].attr
    assert (form['resource'], form['value'], form['formId']) == ('address', '^.', 'c1_form')
    assert form['loadOnBuilt'] is True
    assert form['store_autoSave'] == 500
    assert (form['rootTag'], form['grouplet_rootWidget']) == ('div', 'div'), 'sized by its content'
    assert host_kw(root)['formId'] == 'c1_form'
    scripts = [n.attr for n in nodes_by_tag(root, 'datacontroller')]
    reload = [a for a in scripts if a.get('formsubscribe_onLoaded')][0]
    assert reload['afterSave'] == '=#WORKSPACE.after_save', 'follows the loads of the form around it'
    assert any(a.get('subscribe_form_c1_form_onStatusChange') for a in scripts)


def test_use_form_takes_a_handler_by_name_and_needs_one(card_page):
    root = GnrDomSrc_dojo_11.makeRoot(card_page)

    def shipping_fields(pane, **kwargs):
        pass
    card_page.gr_groupletCard(root.div(), handler=shipping_fields, useForm=True)
    assert nodes_by_tag(root, 'groupletform')[0].attr['handler'] == 'shipping_fields'
    assert nodes_by_tag(root, 'groupletform')[0].attr['store_autoSave'] == 1
    with pytest.raises(StructError):
        card_page.gr_groupletCard(root.div(), useForm=True)
