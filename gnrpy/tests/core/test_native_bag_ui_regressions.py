"""Real GenroPy consumer regressions, isolated across both Bag modes."""

from pathlib import Path

import pytest

from .test_instance_bag_mode import _run


@pytest.fixture(params=['genro-bag', 'legacy'])
def bag_config(tmp_path, request):
    config = tmp_path / 'instanceconfig.xml'
    config.write_text(
        f'<GenRoBag><experimental><bag implementation="{request.param}"/></experimental></GenRoBag>'
    )
    return config


_STRUCT_PAGE = '''
from types import SimpleNamespace
from gnr.web.gnrwebstruct.dojo11 import GnrDomSrc_dojo_11 as GnrDomSrc
class StructPage:
    application = SimpleNamespace(allowedByPreference=lambda **kw: True,
                                  checkResourcePermission=lambda *args: True)
    userTags = ''
    def __init__(self):
        self._register_nodeId = {}
    def checkTablePermission(self, **kwargs):
        return True
root = GnrDomSrc.makeRoot(page=StructPage())
'''


def test_chat_grid_node_by_id_returns_node_attributes(bag_config):
    result = _run(bag_config, _STRUCT_PAGE + '''
branch = root.child('div', childname='branch')
branch.child('div', childname='grid', nodeId='chat_grid')
assert root.nodeById('chat_grid').attr['nodeId'] == 'chat_grid'
assert root.nodeById('chat_grid') is branch.getNode('grid')
assert root.nodeById('missing') is None
''')
    assert result.returncode == 0, result.stderr


def test_product_type_grid_lookup_does_not_load_hierarchical_data(bag_config):
    result = _run(bag_config, _STRUCT_PAGE + '''
from gnr.sql.gnrsqltable_proxy.hierarchical import TableHandlerTreeResolver
class UnloadedTree(TableHandlerTreeResolver):
    def load(self):
        raise AssertionError('Grid lookup expanded hierarchical data')
root.setItem('tree_data', UnloadedTree(table='invc.product_type'))
frame = root.child('div', childname='frame', frameCode='products')
pane = frame.child('div', childname='pane')
view = pane.includedview_inframe(frameCode='products')
assert view.attributes['frameCode'] == 'products'
assert frame.attributes['target'] == 'products_grid'
assert root.getNodeByAttr('frameCode', 'missing') is None
path = []
assert root.getNodeByAttr('frameCode', 'products', path) is root.getNode('frame')
assert path == ['frame']
''')
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize('table', ['invc.invoice', 'invc.customer'])
def test_table_handler_builds_grid_context_menu(bag_config, table):
    repository = Path(__file__).resolve().parents[3]
    result = _run(bag_config, '''
import sys
from types import SimpleNamespace
from gnr.core.gnrlang import gnrImport
module = gnrImport(sys.argv[1])
method = next(cls._th_view_confMenues for cls in vars(module).values()
              if isinstance(cls, type) and '_th_view_confMenues' in vars(cls))
for privileged, count in [(False, 4), (True, 7)]:
    captured = {}
    grid = SimpleNamespace(attributes={'nodeId': 'testgrid', 'table': sys.argv[2]},
                           data=lambda path, bag: captured.update(menu=bag))
    frame = SimpleNamespace(grid=grid, dataRemote=lambda *args, **kwargs: None)
    page = SimpleNamespace(isDeveloper=lambda: privileged,
        application=SimpleNamespace(checkResourcePermission=lambda *args: privileged),
        userTags='', _th_advancedToolsMenu=lambda: None)
    method(page, frame)
    menu = captured['menu']
    assert len(menu) == count
    assert menu.getNode('#0').attr['label'] == '!!Reload'
    assert menu.getNode('#0').attr['_pkey'] == 'R_00000000'
    assert menu.getNode('#0').attr['action'] == '$2.widget.reload();'
''', arguments=(str(repository / 'resources/common/th/th_view.py'), table))
    assert result.returncode == 0, result.stderr


def test_page_resolver_recall_and_rpc_xml_round_trip(bag_config):
    result = _run(bag_config, '''
from types import SimpleNamespace
from gnr.core.gnrbag import Bag, BagResolver
from gnr.core.gnrclasses import GnrClassCatalog
from gnr.web._gnrbasewebpage import GnrBaseWebPage
from gnr.web.gnrwebpage import GnrWebPage
from gnr.web.gnrwebpage_proxy.rpc import GnrWebRpc
class CallbackResolver(BagResolver):
    classKwargs = {'cacheTime': 0, 'readOnly': True, 'record_id': None}
    def load(self):
        return Bag(dict(record_id=self.record_id, page_bound=self._page is page))
page = object.__new__(GnrWebPage)
page.response = SimpleNamespace(content_type=None)
page.site = SimpleNamespace(gnrapp=SimpleNamespace(catalog=GnrClassCatalog()))
page._frontend = SimpleNamespace(domSrcFactory=type('NeverDomSource', (), {}))
page._closed = False
page._subscribe_event = lambda *args: None
page.collectClientDatachanges = lambda: None
page.isLocalizer = lambda: False
page.localize = lambda value: value
assert page.getPublicMethod('rpc', 'resolverRecall').__func__ is GnrBaseWebPage.resolverRecall
proxy = GnrWebRpc(page)
result = proxy(method='resolverRecall', _auth=0, resolverPars={
    'resolverclass': 'CallbackResolver', 'resolvermodule': '__main__',
    'args': [], 'kwargs': {'record_id': 7}})
assert isinstance(result, Bag)
assert result['record_id'] == 7 and result['page_bound'] is True
parsed = Bag(proxy.result_bag(result))
assert parsed['result.record_id'] == 7
assert parsed['result.page_bound'] is True
assert page.response.content_type == 'text/xml'
''')
    assert result.returncode == 0, result.stderr
