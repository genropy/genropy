"""Missing SQL bindings mean NULL across the common execution path."""

import pytest


@pytest.fixture(params=['db_sqlite', 'db_pg', 'db_pg3'])
def db(request):
    return request.getfixturevalue(request.param)


@pytest.mark.parametrize('params', [None, {}, {'root_fkey': None}])
def test_missing_binding_is_null(db, params):
    original = None if params is None else dict(params)
    row = db.execute('SELECT :root_fkey IS NULL AS missing', params).fetchone()
    assert bool(row[0]) is True
    assert params == original


@pytest.mark.parametrize('value', [0, False, '', 'ROOT'])
def test_explicit_binding_and_environment_are_preserved(db, value):
    params = {'root_fkey': value}
    with db.tempEnv(binding_probe='environment'):
        row = db.execute(
            'SELECT :root_fkey AS supplied, :missing IS NULL AS missing, '
            ':env_binding_probe AS context', params).fetchone()
    assert row[0] == value
    assert bool(row[1]) is True
    assert row[2] == 'environment'
    assert params == {'root_fkey': value}
