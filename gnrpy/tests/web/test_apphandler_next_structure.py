"""Equivalence between the structure flows of the two handlers.

``GnrWebAppHandlerNext`` moves the database level part of ``getTablesTree``
and ``dbStructure`` onto a database proxy (``db.structureProxy()``).  It is a
refactoring, so the same path must give the same Bag through both handlers.
"""

import pytest

from gnr.app.gnrsqltable_proxy.db_structure import DbStructureProxy

from apphandler_next_common import (gnr_test_config, db,  # noqa: F401
                                    make_handlers, handlers)


PATHS = ['', 'invc', 'invc.tables', 'invc.tables.invoice',
         'invc.tables.invoice.columns', 'invc.tables.invoice.columns.customer_id']


def test_tables_tree_is_the_same(handlers):  # noqa: F811
    legacy, next_ = handlers
    a, b = legacy.getTablesTree(), next_.getTablesTree()
    assert a.toXml() == b.toXml()
    assert 'invc' in a
    assert a['invc'].getAttr('invoice', 'tableid') == 'invc.invoice'


@pytest.mark.parametrize('path', PATHS)
def test_db_structure_is_the_same(handlers, path):  # noqa: F811
    legacy, next_ = handlers
    a, b = legacy.dbStructure(path=path), next_.dbStructure(path=path)
    assert a.toXml() == b.toXml()


def test_db_structure_on_a_relations_node_raises_in_both(handlers):  # noqa: F811
    """S1: a path that names no node (``relations``, the example of the
    legacy docstring, is not a key of ``DbTableObj``: the keys are ``columns``,
    ``virtual_columns``, ``indexes``, ``table_aliases``) resolves to ``None``
    and the inner walk iterates it; both handlers raise the same ``TypeError``."""
    for handler in handlers:
        with pytest.raises(TypeError):
            handler.dbStructure(path='invc.tables.invoice.relations')


def test_db_structure_sub_trees_are_remote_resolvers(handlers):  # noqa: F811
    _, next_ = handlers
    result = next_.dbStructure(path='invc.tables')
    node = result.getNode('invoice')
    assert node.attr.get('_T') == 'JS'
    assert node.value == "genro.rpc.remoteResolver('app.dbStructure',{path:'invc.tables.invoice'})"


def test_rpc_aliases_are_kept(handlers):  # noqa: F811
    for handler in handlers:
        assert handler.rpc_getTablesTree.__func__ is handler.getTablesTree.__func__
        assert handler.rpc_dbStructure.__func__ is handler.dbStructure.__func__


def test_structure_proxy_is_cached_on_the_db(db):  # noqa: F811
    proxy = db.structureProxy()
    assert isinstance(proxy, DbStructureProxy)
    assert proxy is db.structureProxy()
    assert proxy.db is db
