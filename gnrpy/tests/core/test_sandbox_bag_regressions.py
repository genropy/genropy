"""Sandbox acceptance regressions through actual consumers in both Bag modes."""
import json
from pathlib import Path

import pytest

from .test_instance_bag_mode import _run
from .test_native_bag_ui_regressions import bag_config  # noqa: F401


def test_pwa_configuration_reads_text_stream(bag_config):
    result = _run(bag_config, '''
from io import StringIO
from types import SimpleNamespace
from gnr.web.gnrwsgisite_proxy.gnrpwahandler import PWAHandler
node = SimpleNamespace(exists=True, open=lambda mode: StringIO(
    '<GenRoBag><name> Test PWA </name><short_name> Demo </short_name></GenRoBag>'))
site = SimpleNamespace(db=None, mainpackage='test', storageNode=lambda *a: node,
                       getPreference=lambda *a, **k: None)
assert PWAHandler(site).configuration() == {'name': 'Test PWA', 'short_name': 'Demo'}
''')
    assert result.returncode == 0, result.stderr


def test_menu_resolver_extra_keywords(bag_config):
    result = _run(bag_config, '''
from gnr.web.gnrmenu import MenuResolver
from gnr.core.gnrdict import dictExtract
resolver = MenuResolver(branch_customer='C1')
assert dictExtract(resolver.kwargs, 'branch_') == {'customer': 'C1'}
assert 'cacheTime' not in resolver.kwargs
assert 'path' not in resolver.kwargs
resolver.kwargs['branch_customer'] = 'C2'
assert dictExtract(resolver.kwargs, 'branch_') == {'customer': 'C2'}
''')
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize('name', ['SqlRelatedRecordResolver', 'SqlRelatedSelectionResolver'])
def test_sql_resolver_defaults_and_metadata(bag_config, name):
    result = _run(bag_config, '''
import sys
from gnr.core.gnrbag import Bag
from gnr.sql.gnrsqldata import record
Resolver = getattr(record, sys.argv[1])
resolver = Resolver(cacheTime=-1, output_mode='bag')
assert resolver.readOnly is True
calls = []
def load():
    calls.append(resolver.output_mode)
    return Bag({'child': 1})
resolver.load = load
bag = Bag()
bag.setItem('relation', resolver, mode='O')
node = bag.getNode('relation')
assert bag['relation']['child'] == 1
assert bag['relation']['child'] == 1
assert calls == ['bag']
assert node._value is None
assert Resolver(cacheTime=-1, readOnly=False).readOnly is False
''', arguments=[name])
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize('root_key', [None, 'ROOT', 0])
def test_tree_root_bind_matches_condition(bag_config, root_key):
    module = Path(__file__).resolve().parents[3] / 'resources/common/th/th_tree.py'
    result = _run(bag_config, '''
import sys, json
from types import SimpleNamespace as NS
from gnr.core.gnrlang import gnrImport
from gnr.core.gnrbag import Bag
module = gnrImport(sys.argv[1])
key = json.loads(sys.argv[2])
store = NS(attributes={'_fkey_name': 'parent_id'})
grid = NS(attributes={})
th = NS(view=NS(store=store, grid=grid), attributes={'table': 'pkg.child'})
tree = NS(attributes={}, getInheritedAttributes=lambda: {'table': 'pkg.parent'},
          dataController=lambda *a, **k: None)
table = NS(pkg=NS(tables={'parent_alias': None}))
page = NS(db=NS(table=lambda name: table))
module.TableHandlerHierarchicalView.ht_relatedTableHandler(
    page, tree, th, root_fkey=key)
attrs = store.attributes
assert attrs['root_fkey'] == key
assert ':root_fkey' in attrs['condition']
bag = Bag()
bag.setItem('store', None, _attributes=attrs)
params = dict(bag.getNode('store').attr)
assert ('root_fkey' in params) == (key is not None)
# Execute the original tree predicate even when normalization omitted None.
from gnr.sql.gnrsql import GnrSqlDb
db = GnrSqlDb(implementation='sqlite', dbname=':memory:')
condition = params.pop('condition').replace(
    '@parent_id.hierarchical_pkey', 'hpkey').replace('$parent_id', 'parent_id')
# SQLite accepts IS TRUE on binds directly; only ILIKE needs translation.
condition = condition.replace(' ILIKE ', ' LIKE ')
params.update(fkey=key, showInherited=False, curr_hpkey='branch')
try:
    row = db.execute(
        'SELECT ' + condition + ' FROM '
        "(SELECT NULL AS parent_id, 'branch/child' AS hpkey)",
        params, _adaptArguments=False).fetchone()
    assert row[0] == 1
finally:
    db.closeConnection()
''', arguments=[str(module), json.dumps(root_key)])
    assert result.returncode == 0, result.stderr
