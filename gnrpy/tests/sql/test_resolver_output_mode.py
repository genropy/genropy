"""SQL output format and relation cardinality have separate parameter names."""

import pytest

from gnr.core.gnrbag import Bag
from gnr.sql.gnrsqldata.record import (
    SqlRelatedRecordResolver, SqlRelatedSelectionResolver,
)


@pytest.fixture(params=['db_sqlite', 'db_pg', 'db_pg3'])
def db(request):
    return request.getfixturevalue(request.param)


@pytest.fixture
def invoice(db):
    return db.table('invc.invoice').query(
        columns='$id,$customer_id', limit=1).fetch()[0]


def assert_wire_roundtrip(resolver, output_mode, db):
    description = resolver.resolverSerialize()
    kwargs = dict(description['kwargs'])
    assert kwargs['output_mode'] == output_mode
    assert 'mode' not in kwargs
    assert kwargs.pop('_serialized_app_db') == 'maindb'
    kwargs['db'] = db
    return type(resolver)(*description['args'], **kwargs)


def test_record_relation_preserves_cardinality_and_output_mode(db, invoice):
    record = db.table('invc.invoice').record(pkey=invoice['id']).output('bag')
    node = record.getNode('@customer_id')
    resolver = node.resolver
    assert isinstance(resolver, SqlRelatedRecordResolver)
    assert node.attr['mode'] == 'O'
    assert 'mode' not in resolver.classKwargs
    assert resolver.output_mode == 'bag'
    assert node.getValue()['id'] == invoice['customer_id']
    restored = assert_wire_roundtrip(resolver, 'bag', db)
    target = Bag()
    target.setItem('customer', restored, mode='O')
    assert target['customer']['id'] == invoice['customer_id']


def test_selection_resolver_preserves_cardinality_and_output_mode(db, invoice):
    resolver = SqlRelatedSelectionResolver(
        db=db, output_mode='grid', target_fld='invc.invoice.customer_id',
        relation_value=invoice['customer_id'], sqlparams={})
    bag = Bag()
    bag.setItem('invoices', resolver, mode='M')
    assert 'mode' not in resolver.classKwargs
    result = bag['invoices']
    assert isinstance(result, Bag)
    assert len(result) > 0
    assert bag.getNode('invoices').attr['mode'] == 'M'
    restored = assert_wire_roundtrip(resolver, 'grid', db)
    other = Bag()
    other.setItem('invoices', restored, mode='M')
    assert len(other['invoices']) == len(result)


@pytest.mark.parametrize('format_name', ['bag', 'selection', 'grid'])
def test_selection_record_resolver_factories(db, invoice, format_name):
    selection = db.table('invc.invoice').query(
        where='$id=:pkey', pkey=invoice['id']).selection()
    result = selection.output(format_name, recordResolver=True)
    row = (result['rows'] if format_name == 'bag' else result).getNode('#0')
    node = row.getValue().getNode('_') if format_name == 'bag' else row
    assert isinstance(node.resolver, SqlRelatedRecordResolver)
    assert node.resolver.output_mode == 'bag'
    assert node.getValue()['id'] == invoice['id']


def test_reverse_relation_factory_uses_output_mode(db, invoice):
    record = db.table('invc.customer').record(
        pkey=invoice['customer_id']).output('bag')
    nodes = [node for node in record.getNodes()
             if isinstance(node.resolver, SqlRelatedSelectionResolver)
             and node.resolver.target_fld == 'invc.invoice.customer_id']
    assert len(nodes) == 1
    node = nodes[0]
    assert node.attr['mode'] == 'M'
    assert node.resolver.output_mode == 'grid'
    assert len(node.getValue()) > 0
