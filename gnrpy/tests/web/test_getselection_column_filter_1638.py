"""getSelection grouped by one column for the grid column filter (#1638).

The grid replays its own query with ``selectmethod='app.columnFilterSelect'``:
each row is one value of the filtered column, with its caption and how many
records of the current query carry it.  The database is the real
``test_invoice`` project on postgres, with the page stand-in of the saved
query tests.
"""

import pytest

from web.test_getselection_saved_query_1359 import (  # noqa: F401
    NSW_CUSTOMERS, _StandInPage, db_postgres, gnr_test_config)

from gnr.web.gnrwebpage_proxy.apphandler import GnrWebAppHandler


@pytest.fixture
def handler(db_postgres, tmp_path):  # noqa: F811
    page = _StandInPage(db_postgres, str(tmp_path))
    handler = GnrWebAppHandler(page)
    page.rpc_methods['app.columnFilterSelect'] = handler.columnFilterSelect
    return handler


def _groups(result):
    data, _ = result
    return {node.attr['cf_value']: node.attr for node in data}


def test_counts_cover_the_whole_query(handler, db_postgres):  # noqa: F811
    groups = _groups(handler.getSelection(table='invc.customer', columns='$state',
                                          selectmethod='app.columnFilterSelect',
                                          columnFilterField='$state'))
    assert groups['NSW']['cf_count'] == NSW_CUSTOMERS
    assert 'cf_caption' not in groups['NSW']
    total = db_postgres.table('invc.customer').query().count()
    assert sum(g['cf_count'] for g in groups.values()) == total


def test_counts_follow_the_condition(handler):
    groups = _groups(handler.getSelection(table='invc.customer', columns='$state',
                                          selectmethod='app.columnFilterSelect',
                                          columnFilterField='$state',
                                          condition='$state IN :colfilter_state',
                                          colfilter_state=['NSW', 'VIC']))
    assert set(groups) == {'NSW', 'VIC'}
    assert groups['NSW']['cf_count'] == NSW_CUSTOMERS


def test_related_field_groups_by_id_with_its_caption(handler, db_postgres):  # noqa: F811
    groups = _groups(handler.getSelection(table='invc.invoice', columns='$customer_id',
                                          selectmethod='app.columnFilterSelect',
                                          columnFilterField='$customer_id',
                                          columnFilterCaption='@customer_id.account_name'))
    invoices = db_postgres.table('invc.invoice').query(columns='$customer_id,@customer_id.account_name AS name').fetch()
    expected = {}
    for row in invoices:
        expected.setdefault(row['customer_id'], [row['name'], 0])[1] += 1
    assert {k: [g['cf_caption'], g['cf_count']] for k, g in groups.items()} == expected


def test_field_must_be_a_field_path(handler):
    with pytest.raises(ValueError):
        handler.columnFilterSelect(columnFilterField='$state; DROP TABLE x', table='invc.customer')
