"""adapter.string_join and the __protecting_reasons / __invalid_reasons
formulas built on it (#1485), run on SQLite and PostgreSQL."""

import pytest

TAG_MARKER = '__string_join_test__'


@pytest.fixture(params=['db_sqlite', 'db_pg'])
def db(request):
    return request.getfixturevalue(request.param)


def _case(value):
    if value is None:
        return "( CASE WHEN 1=0 THEN 'x' ELSE NULL END )"
    return "( CASE WHEN 1=1 THEN '%s' ELSE NULL END )" % value


@pytest.mark.parametrize('values,expected', [
    (['a', None, 'b'], 'a,b'),
    ([None, 'a'], 'a'),
    (['a', ''], 'a,'),
    ([None, None], ''),
])
def test_string_join_skips_nulls(db, values, expected):
    sql = 'SELECT %s' % db.adapter.string_join([_case(v) for v in values], ',')
    assert db.execute(sql).fetchone()[0] == expected


def _cleanup(db):
    tbl = db.table('adm.htag')
    tbl.sql_deleteSelection(where='$note = :marker', marker=TAG_MARKER)
    db.commit()


def test_protecting_and_invalid_reasons(db):
    tbl = db.table('adm.htag')
    _cleanup(db)
    try:
        for code, syscode in [('sjplain', None), ('sjsys', 'SJSYS'),
                              ('sjdup', '_ERR_DUP_SJ')]:
            tbl.insert(dict(code=code, description=code, __syscode=syscode,
                            note=TAG_MARKER))
        db.commit()
        with db.tempEnv(userTags='user'):
            rows = tbl.query(
                columns='$code,$__protecting_reasons,$__is_protected_row,'
                        '$__invalid_reasons,$__is_invalid_row',
                where='$note = :marker', marker=TAG_MARKER).fetch()
        result = {r['code']: (r['__protecting_reasons'], bool(r['__is_protected_row']),
                              r['__invalid_reasons'], bool(r['__is_invalid_row']))
                  for r in rows}
        assert result == {
            'sjplain': ('', False, '', False),
            'sjsys': ('syscode', True, '', False),
            'sjdup': ('syscode', True, 'duplicate_sysrecord', True),
        }
    finally:
        _cleanup(db)
