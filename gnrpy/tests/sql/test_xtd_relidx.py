# -*- coding: utf-8 -*-
"""XTD side tables and relidx numbering (issue #1889).

Package xtd_test of the test_invoice_xtd instance: xtd_test.doc is the master,
with pkey 'code' rather than 'id', xtd_test.doc_xtd its XTD table and
xtd_test.doc_line the detail declared with sysFields(relidx='doc_code').
Every test runs on SQLite and on PostgreSQL.
"""

import datetime
import os
import re

import pytest

from gnr.app.gnrapp import GnrApp
from gnr.sql.gnrsql_exceptions import NotMatchingModelError

from core.common import BaseGnrTest
from .conftest import _db_pg

DOC = 'xtd_test.doc'
LINE = 'xtd_test.doc_line'
XTD = 'xtd_test.doc_xtd'
COUNTER = 'xtd_test_doc_line_relidx'


def setup_module(module):
    BaseGnrTest.setup_class()


def teardown_module(module):
    BaseGnrTest.teardown_class()


@pytest.fixture(scope='module', params=['sqlite', 'postgres'])
def db(request, sqlite_temp_dir):
    if request.param == 'postgres':
        yield from _db_pg(request, 'postgres', instance='test_invoice_xtd')
        return
    app = GnrApp('test_invoice_xtd', db_attrs=dict(
        implementation='sqlite', dbname=os.path.join(sqlite_temp_dir, 'xtd')))
    app.db.model.check(applyChanges=True)
    yield app.db
    app.db.closeConnection()


def new_doc(db, code, lines=0):
    db.table(DOC).insert(dict(code=code))
    added = add_lines(db, code, lines)
    db.commit()
    return added


def add_lines(db, code, n):
    tbl = db.table(LINE)
    added = []
    for i in range(n):
        record = dict(doc_code=code, description='%s-%i' % (code, i))
        tbl.insert(record)
        added.append(record['id'])
    db.commit()
    return added


def relidx_by_line(db, code):
    rows = db.table(LINE).query(columns='$_relidx', where='$doc_code=:code',
                                code=code).fetch()
    return {r['pkey']: r['_relidx'] for r in rows}


def counter(db, code):
    return db.table(XTD).readColumns(columns='$%s' % COUNTER,
                                     where='$main_id=:code', code=code)


def scramble(db, line_ids, days):
    """Clear _relidx and give each line the insert date of the matching day."""
    tbl = db.table(LINE)
    for line_id, day in zip(line_ids, days):
        tbl.raw_update(dict(id=line_id, _relidx=None,
                            __ins_ts=datetime.datetime(2026, 1, day)),
                       dict(id=line_id))
    db.commit()


def test_numbering_is_relative_to_the_master(db):
    a = new_doc(db, 'NUM_A', lines=3)
    b = new_doc(db, 'NUM_B', lines=2)
    assert relidx_by_line(db, 'NUM_A') == dict(zip(a, [1, 2, 3]))
    assert relidx_by_line(db, 'NUM_B') == dict(zip(b, [1, 2]))
    assert counter(db, 'NUM_A') == 3
    assert counter(db, 'NUM_B') == 2


def test_deleted_line_leaves_a_gap(db):
    first, second, third = new_doc(db, 'GAP', lines=3)
    db.table(LINE).delete(second)
    db.commit()
    [fourth] = add_lines(db, 'GAP', 1)
    assert relidx_by_line(db, 'GAP') == {first: 1, third: 3, fourth: 4}
    assert counter(db, 'GAP') == 4


def test_master_delete_removes_lines_and_xtd_row(db):
    new_doc(db, 'DEL', lines=2)
    db.table(DOC).delete('DEL')
    db.commit()
    assert relidx_by_line(db, 'DEL') == {}
    assert db.table(XTD).query(where='$main_id=:code', code='DEL').count() == 0


def test_realign_one_master(db):
    lines = new_doc(db, 'REAL', lines=4)
    db.table(LINE).delete(lines.pop())
    db.commit()
    assert counter(db, 'REAL') == 4
    scramble(db, lines, days=[3, 1, 2])
    db.table(DOC).xtd.realignRelatedRelIdx('REAL')
    db.commit()
    assert relidx_by_line(db, 'REAL') == dict(zip(lines, [3, 1, 2]))
    assert counter(db, 'REAL') == 3


def test_realign_all_masters(db):
    first = new_doc(db, 'ALL_A', lines=2)
    second = new_doc(db, 'ALL_B', lines=3)
    scramble(db, first, days=[2, 1])
    scramble(db, second, days=[1, 3, 2])
    db.table(DOC).xtd.realignRelatedRelIdxAll()
    db.commit()
    assert relidx_by_line(db, 'ALL_A') == dict(zip(first, [2, 1]))
    assert relidx_by_line(db, 'ALL_B') == dict(zip(second, [1, 3, 2]))
    assert counter(db, 'ALL_A') == 2
    assert counter(db, 'ALL_B') == 3


def test_xtd_handler_delegates_and_refuses_unknown_names(db):
    xtd = db.table(DOC).xtd
    assert xtd.fullname == XTD
    with pytest.raises(AttributeError):
        xtd.no_such_method


def test_xtd_relation_follows_master_pkey(db):
    joiner = db.table(DOC).relations.getAttr('@xtd')['joiner']
    assert joiner['one_relation'] == 'xtd_test.doc.code'


def test_xtd_caption_names_existing_columns(db):
    tbl = db.table(XTD)
    caption_field = tbl.attributes.get('caption_field')
    assert caption_field is None or caption_field in tbl.columns
    rowcaption = tbl.attributes.get('rowcaption') or ''
    assert all(name in tbl.columns for name in re.findall(r'\$(\w+)', rowcaption))


def test_relidx_without_xtd_module_is_refused(db):
    with pytest.raises(NotMatchingModelError) as excinfo:
        db.table(LINE).addRelXtdRelidxColumn(reltbl='invc.invoice_row', relidx='invoice_id')
    assert 'invc/invoice_xtd' in str(excinfo.value)
