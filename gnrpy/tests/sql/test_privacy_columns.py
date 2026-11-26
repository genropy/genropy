"""Tests for the personal data marks: masked modes, listing and census.

Tests cover:
1. mask_field_sql — the privacy modes on SQLite and PostgreSQL
2. masked variant columns — end to end on adm.user and on a date column
3. SqlTable.privacy_columns — kinds, marks without a kind, encrypted columns
4. privacy_report — TSV census and the guarantee that it reads no table data
"""

import os

import pytest

from gnr.app.gnrapp import GnrApp
from gnr.sql.adapters.gnrsqlite import GnrSqliteCursor
from gnr.sql.gnrsqlprivacy import (is_suspect_column, privacy_report,
                                   privacy_report_text, privacy_report_tsv)

from core.common import BaseGnrTest


def setup_module(module):
    """Configure genro environment for GnrApp-based fixtures."""
    BaseGnrTest.setup_class()


def teardown_module(module):
    BaseGnrTest.teardown_class()


@pytest.fixture(scope='module', params=['sqlite', 'pg'])
def any_db(request):  # wf:phase-1:new
    return request.getfixturevalue('db_%s' % request.param)


def masked_literal(db, value, mode):  # wf:phase-1:new
    """Mask a SQL literal with the adapter's expression and return the result."""
    expr = db.adapter.mask_field_sql(value, mode=mode)
    return db.execute('SELECT %s' % expr).fetchall()[0][0]


# ---------------------------------------------------------------------------
#  1. Privacy modes of mask_field_sql
# ---------------------------------------------------------------------------

class TestMaskModes:

    @pytest.mark.parametrize('value,mode,expected', [
        ("'RSSMRA80A01H501U'", 'cf', 'RSS************U'),
        ("'01234567890'", 'piva', '01******890'),
        ("'IT60X0542811101000000123456'", 'iban', 'IT60' + '*' * 19 + '3456'),
        ("'Mario'", 'name', 'M***'),
        ("'Massimiliano'", 'name', 'M***'),
        ("'Via Roma 12'", 'address', 'Via***'),
        ("'1980-05-17'", 'birthdate', '1980-**-**'),
        ("'any free text'", 'text', '***'),
    ])
    def test_new_modes(self, any_db, value, mode, expected):  # wf:phase-1:new
        assert masked_literal(any_db, value, mode) == expected

    @pytest.mark.parametrize('mode', ['cf', 'piva', 'iban', 'name', 'address',
                                      'birthdate', 'text'])
    def test_null_stays_null(self, any_db, mode):  # wf:phase-1:new
        assert masked_literal(any_db, 'NULL', mode) is None

    @pytest.mark.parametrize('value,mode,expected', [
        ("'mario.rossi@example.com'", 'email', 'ma' + '*' * 9 + '@example.com'),
        ("'4111111111111111'", 'creditcard', '************1111'),
        ("'+393331234567'", 'phone', '+39*******567'),
        ("'ABCDEFGHIJ'", '2-4', 'AB****GHIJ'),
    ])
    def test_existing_modes_unchanged(self, any_db, value, mode, expected):  # wf:phase-1:new
        assert masked_literal(any_db, value, mode) == expected


# ---------------------------------------------------------------------------
#  2. masked variant columns, end to end
# ---------------------------------------------------------------------------

class TestMaskedVariantColumns:

    def test_user_columns_masked(self, any_db):  # wf:phase-1:new
        row = any_db.table('adm.user').query(
            columns='$firstname_masked, $lastname_masked, $email_masked',
            where='$username = :u', u='james.wilson',
        ).fetch()[0]
        assert row['firstname_masked'] == 'J***'
        assert row['lastname_masked'] == 'W***'
        assert row['email_masked'] == 'ja' + '*' * 10 + '@testinvoice.com'

    def test_date_column_masked(self, any_db):  # wf:phase-1:new
        tbl = any_db.table('invc.invoice')
        expr = any_db.adapter.mask_field_sql('$date', mode='birthdate')
        rows = tbl.query(columns='$date, %s AS date_masked' % expr, limit=5).fetch()
        assert rows
        for row in rows:
            assert row['date_masked'] == '%s-**-**' % row['date'].year

    def test_date_column_generic_mode(self, any_db):  # wf:phase-1:new
        tbl = any_db.table('invc.invoice')
        expr = any_db.adapter.mask_field_sql('$date', mode='4-2')
        row = tbl.query(columns='$date, %s AS date_masked' % expr, limit=1).fetch()[0]
        assert row['date_masked'] == '%s****%02d' % (row['date'].year, row['date'].day)


# ---------------------------------------------------------------------------
#  3. SqlTable.privacy_columns
# ---------------------------------------------------------------------------

class TestPrivacyColumns:

    def test_kinds(self, db_sqlite):  # wf:phase-1:new
        marked = db_sqlite.table('adm.user').privacy_columns
        assert marked['email'] == 'email'
        assert marked['firstname'] == 'name'
        assert marked['mobile'] == 'phone'
        assert 'username' not in marked

    def test_encrypted_alone_has_no_kind(self, db_sqlite):  # wf:phase-1:new
        assert db_sqlite.table('invc.customer').privacy_columns == {
            'access_token': None, 'bank_account': None, 'registration_id': None,
        }

    def test_mark_without_mode(self, db_sqlite, monkeypatch):  # wf:phase-1:new
        colobj = db_sqlite.model.column('invc.customer.notes')
        monkeypatch.setitem(colobj.attributes, 'variant', 'masked')
        assert db_sqlite.table('invc.customer').privacy_columns['notes'] is None

    def test_masked_in_variant_list(self, db_sqlite, monkeypatch):  # wf:phase-1:new
        colobj = db_sqlite.model.column('invc.customer.street_address')
        monkeypatch.setitem(colobj.attributes, 'variant', 'unaccent,masked')
        monkeypatch.setitem(colobj.attributes, 'variant_masked_mode', 'address')
        assert db_sqlite.table('invc.customer').privacy_columns['street_address'] == 'address'

    def test_encrypted_and_masked_keeps_kind(self, db_sqlite, monkeypatch):  # wf:phase-1:new
        colobj = db_sqlite.model.column('invc.customer.bank_account')
        monkeypatch.setitem(colobj.attributes, 'variant', 'masked')
        monkeypatch.setitem(colobj.attributes, 'variant_masked_mode', 'iban')
        assert db_sqlite.table('invc.customer').privacy_columns['bank_account'] == 'iban'


# ---------------------------------------------------------------------------
#  4. privacy_report
# ---------------------------------------------------------------------------

class TestSuspectColumns:

    @pytest.mark.parametrize('colname', [
        'codice_fiscale', 'cliente_cf', 'email_pec', 'tel', 'home_address',
        'data_nascita', 'name', 'notes', 'Partita_IVA', 'vat_number',
    ])
    def test_suspect(self, colname):  # wf:phase-1:new
        assert is_suspect_column(colname)

    @pytest.mark.parametrize('colname', [
        'cfg', 'nomenclature', 'username', 'telemetry', 'viaggio', 'notebook',
        'customer_type_code', 'total',
    ])
    def test_not_suspect(self, colname):  # wf:phase-1:new
        assert not is_suspect_column(colname)


class TestPrivacyReport:

    def test_tsv(self, db_sqlite):  # wf:phase-1:new
        lines = privacy_report_tsv(privacy_report(db_sqlite)).splitlines()
        assert lines[0] == 'package\ttable\tcolumn\tstatus\tkind'
        rows = {tuple(line.split('\t')) for line in lines[1:]}
        assert ('adm', 'adm.user', 'email', 'marked', 'email') in rows
        assert ('invc', 'invc.customer', 'bank_account', 'nokind', '') in rows
        assert ('invc', 'invc.customer', 'street_address', 'suspect', '') in rows
        assert ('invc', 'invc.customer', 'phone', 'suspect', '') in rows
        assert not any(row[2] == 'username' for row in rows)
        assert all(len(row) == 5 for row in rows)

    def test_physical_columns_only(self, db_sqlite):  # wf:phase-1:new
        rows = privacy_report(db_sqlite)
        assert not any(column.endswith('_masked') for _, _, column, _, _ in rows)

    def test_declaring_package(self, db_sqlite, monkeypatch):  # wf:phase-1:new
        colobj = db_sqlite.model.column('adm.user.email')
        monkeypatch.setitem(colobj.attributes, '_owner_package', 'invc')
        rows = privacy_report(db_sqlite)
        assert ('invc', 'adm.user', 'email', 'marked', 'email') in rows

    def test_text(self, db_sqlite):  # wf:phase-1:new
        text = privacy_report_text(privacy_report(db_sqlite))
        assert 'invc.customer' in text
        assert 'suspect' in text

    def test_reads_no_table_data(self, sqlite_temp_dir, monkeypatch):  # wf:phase-1:new
        """Loading the instance and running the report query no table."""
        statements = []
        original_execute = GnrSqliteCursor.execute

        def recording_execute(cursor, sql, *args, **kwargs):
            statements.append(sql)
            return original_execute(cursor, sql, *args, **kwargs)

        monkeypatch.setattr(GnrSqliteCursor, 'execute', recording_execute)
        app = GnrApp('test_invoice', db_attrs=dict(
            implementation='sqlite',
            dbname=os.path.join(sqlite_temp_dir, 'privacy_nodata'),
        ))
        rows = privacy_report(app.db)
        assert rows
        sqlnames = {tblobj.sqlname.lower()
                    for pkg in app.db.packages.values()
                    for tblobj in pkg.tables.values()}
        touched = [sql for sql in statements
                   if any(name in sql.lower() for name in sqlnames)]
        assert touched == []
        # the recorder is wired: a statement run now is seen
        app.db.execute('SELECT 1')
        assert statements


class TestOwnerPackage:
    """The declaring package of a column added through model/_packages/."""

    @pytest.fixture(scope='class')
    def xtd_db(self, sqlite_temp_dir):  # wf:phase-1:new
        # xtd_test adds invc.customer.xtd_reference from model/_packages/invc/
        return GnrApp('test_invoice_xtd', db_attrs=dict(
            implementation='sqlite',
            dbname=os.path.join(sqlite_temp_dir, 'privacy_owner'),
        )).db

    def test_plugged_column_owner(self, xtd_db):  # wf:phase-1:new
        customer = xtd_db.model.table('invc.customer')
        assert customer.column('xtd_reference').attributes['_owner_package'] == 'xtd_test'
        assert customer.pluggedColumns() == ['xtd_reference']

    def test_later_columns_keep_their_package(self, xtd_db):  # wf:phase-1:new
        """Tables built after the customization are not stamped with its package."""
        for tblname in ('invc.customer_type', 'invc.invoice', 'invc.staff'):
            assert xtd_db.model.table(tblname).pluggedColumns() == []
