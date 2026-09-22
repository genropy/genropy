"""adm.userobject flag columns must be readable on SQLite too (bug #1360).

is_mail/is_row/is_print are static virtual columns, so the compiler adds them to
every record query on the table: the postgres only string_to_array()/ANY() they
used to carry made any read of adm.userobject fail on SQLite with
``no such function: string_to_array``, loadUserObject included.

The pg/sqlite parity pair stays in gnrpy/tests/sql/test_userobject_flags.py,
where the db_pg fixture lives: its subject is the adapter helper rather than
adm. What belongs to the package is here, and it builds a throwaway
application on a temporary sqlite file, as test_notification_audience.py does.
"""
import os
import shutil
import tempfile

from gnr.app.gnrapp import GnrApp


MARKER = '__userobject_flags_test__'

# code, flags, expected (is_mail, is_row, is_print)
CASES = [
    ('UOFLAGS_ROWPRINT', 'is_row,is_print', (False, True, True)),
    ('UOFLAGS_MAIL', 'is_mail', (True, False, False)),
    ('UOFLAGS_EMPTY', '', (False, False, False)),
    ('UOFLAGS_NULL', None, (None, None, None)),
]

FLAG_COLUMNS = ('is_mail', 'is_row', 'is_print')


def _tristate(value):
    """SQLite yields 0/1 for a computed boolean where postgres yields False/True."""
    return None if value is None else bool(value)


def _flags_of(row):
    return tuple(_tristate(row[c]) for c in FLAG_COLUMNS)


class TestUserObjectFlagsSqlite:
    """Every read of adm.userobject used to raise OperationalError on SQLite."""

    @classmethod
    def setup_class(cls):
        cls.instance_name = os.environ.get('GNR_TESTING_INSTANCE_NAME') or 'gnrdevelop'
        cls.temp_dir = tempfile.mkdtemp(prefix='gnr_userobject_flags_')
        cls.app = GnrApp(cls.instance_name, db_attrs=dict(
            implementation='sqlite',
            dbname=os.path.join(cls.temp_dir, 'testing')))
        cls.db = cls.app.db
        cls.db.model.check(applyChanges=True)
        cls.tbl = cls.db.table('adm.userobject')

    @classmethod
    def teardown_class(cls):
        cls.db.closeConnection()
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def setup_method(self):
        self._cleanup()
        for code, flags, _expected in CASES:
            self.tbl.insert(dict(data=None, code=code, tbl='invc.customer',
                                 objtype='query', flags=flags, description=MARKER))
        self.db.commit()

    def teardown_method(self):
        self._cleanup()

    def _cleanup(self):
        for r in self.tbl.query(where='$description = :marker', marker=MARKER,
                                excludeLogicalDeleted=False).fetch():
            self.tbl.delete(r)
        self.db.commit()

    def test_record_reads_flags(self):
        for code, _flags, expected in CASES:
            record = self.tbl.record(where='$code = :code', code=code).output('dict')
            assert _flags_of(record) == expected, code

    def test_query_reads_flags(self):
        rows = self.tbl.query(columns='$code,$is_mail,$is_row,$is_print',
                              where='$description = :marker', marker=MARKER).fetch()
        found = {r['code']: _flags_of(r) for r in rows}
        assert found == {code: expected for code, _flags, expected in CASES}

    def test_filter_on_flag(self):
        rows = self.tbl.query(columns='$code',
                              where='$description = :marker AND $is_row IS TRUE',
                              marker=MARKER).fetch()
        assert [r['code'] for r in rows] == ['UOFLAGS_ROWPRINT']

    def test_load_user_object(self):
        _data, metadata = self.tbl.loadUserObject(userObjectIdOrCode='UOFLAGS_ROWPRINT',
                                                  objtype='query', table='invc.customer')
        assert metadata['code'] == 'UOFLAGS_ROWPRINT'
        assert metadata['flags'] == 'is_row,is_print'
