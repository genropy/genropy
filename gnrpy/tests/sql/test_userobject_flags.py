"""adm.userobject flag columns must be readable on SQLite too (bug #1360).

is_mail/is_row/is_print are static virtual columns, so the compiler adds them to
every record query on the table: the postgres only string_to_array()/ANY() they
used to carry made any read of adm.userobject fail on SQLite with
``no such function: string_to_array``, loadUserObject included.

The tests run the real model on both dialects and compare the results.
"""

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


def _cleanup(db):
    tbl = db.table('adm.userobject')
    for r in tbl.query(where='$description = :marker', marker=MARKER,
                       excludeLogicalDeleted=False).fetch():
        tbl.delete(r)
    db.commit()


def _insert_cases(db):
    tbl = db.table('adm.userobject')
    for code, flags, _expected in CASES:
        tbl.insert(dict(data=None, code=code, tbl='invc.customer',
                        objtype='query', flags=flags, description=MARKER))
    db.commit()


def _populated(db):
    _cleanup(db)
    _insert_cases(db)


class TestUserObjectFlagsSqlite:
    """Every read of adm.userobject used to raise OperationalError on SQLite."""

    def test_record_reads_flags(self, db_sqlite):
        _populated(db_sqlite)
        try:
            tbl = db_sqlite.table('adm.userobject')
            for code, _flags, expected in CASES:
                record = tbl.record(where='$code = :code', code=code).output('dict')
                assert _flags_of(record) == expected, code
        finally:
            _cleanup(db_sqlite)

    def test_query_reads_flags(self, db_sqlite):
        _populated(db_sqlite)
        try:
            tbl = db_sqlite.table('adm.userobject')
            rows = tbl.query(columns='$code,$is_mail,$is_row,$is_print',
                             where='$description = :marker', marker=MARKER).fetch()
            found = {r['code']: _flags_of(r) for r in rows}
            assert found == {code: expected for code, _flags, expected in CASES}
        finally:
            _cleanup(db_sqlite)

    def test_filter_on_flag(self, db_sqlite):
        _populated(db_sqlite)
        try:
            tbl = db_sqlite.table('adm.userobject')
            rows = tbl.query(columns='$code',
                             where='$description = :marker AND $is_row IS TRUE',
                             marker=MARKER).fetch()
            assert [r['code'] for r in rows] == ['UOFLAGS_ROWPRINT']
        finally:
            _cleanup(db_sqlite)

    def test_load_user_object(self, db_sqlite):
        _populated(db_sqlite)
        try:
            tbl = db_sqlite.table('adm.userobject')
            _data, metadata = tbl.loadUserObject(userObjectIdOrCode='UOFLAGS_ROWPRINT',
                                                 objtype='query', table='invc.customer')
            assert metadata['code'] == 'UOFLAGS_ROWPRINT'
            assert metadata['flags'] == 'is_row,is_print'
        finally:
            _cleanup(db_sqlite)


class TestUserObjectFlagsPgVsSqlite:
    """The flag columns must hold the same values on both dialects."""

    def test_same_flags(self, db_pg, db_sqlite):
        for db in (db_pg, db_sqlite):
            _populated(db)
        try:
            results = {}
            for name, db in (('pg', db_pg), ('sqlite', db_sqlite)):
                tbl = db.table('adm.userobject')
                rows = tbl.query(columns='$code,$is_mail,$is_row,$is_print',
                                 where='$description = :marker', marker=MARKER).fetch()
                results[name] = {r['code']: _flags_of(r) for r in rows}
            expected = {code: exp for code, _flags, exp in CASES}
            assert results['pg'] == expected
            assert results['sqlite'] == expected
        finally:
            for db in (db_pg, db_sqlite):
                _cleanup(db)

    def test_same_records(self, db_pg, db_sqlite):
        for db in (db_pg, db_sqlite):
            _populated(db)
        try:
            for code, _flags, expected in CASES:
                values = {}
                for name, db in (('pg', db_pg), ('sqlite', db_sqlite)):
                    record = db.table('adm.userobject').record(
                        where='$code = :code', code=code).output('dict')
                    values[name] = _flags_of(record)
                assert values['pg'] == values['sqlite'] == expected, code
        finally:
            for db in (db_pg, db_sqlite):
                _cleanup(db)

