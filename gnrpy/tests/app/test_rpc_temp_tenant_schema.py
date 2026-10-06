from types import SimpleNamespace

from gnr.core.gnrbag import Bag
from gnr.web.gnrwebpage import GnrWebPage


def _page(db, temp_tenant_schema=None, pageArgs=None, call_kwargs=None):
    return SimpleNamespace(
        _db=None,
        application=SimpleNamespace(db=db),
        globalStore=lambda: Bag(),
        dbstore=None,
        _call_kwargs=call_kwargs or {},
        workdate=None, locale='en-US', default_language='en', language='en',
        user=None, userTags=None, pagename='test', mainpackage=None,
        external_host=None, currentDomain=None, avatar=None,
        site=None, page_id=None,
        pageArgs=pageArgs or {},
        temp_tenant_schema=temp_tenant_schema,
    )


def _env(db, **kwargs):
    return GnrWebPage.db.fget(_page(db, **kwargs)).currentEnv


def test_call_tenant_schema_reaches_the_db_env(db_sqlite):
    assert _env(db_sqlite, temp_tenant_schema='foo')['tenant_schema'] == 'foo'


def test_no_call_tenant_schema_leaves_the_env_alone(db_sqlite):
    assert 'tenant_schema' not in _env(db_sqlite)


def test_call_tenant_schema_wins_over_the_page_args(db_sqlite):
    env = _env(db_sqlite, temp_tenant_schema='foo',
               pageArgs={'env_tenant_schema': 'bar'})
    assert env['tenant_schema'] == 'foo'


def test_page_args_apply_without_a_call_tenant_schema(db_sqlite):
    env = _env(db_sqlite, pageArgs={'env_tenant_schema': 'bar'})
    assert env['tenant_schema'] == 'bar'


def test_explicit_dbenv_wins_over_the_call_tenant_schema(db_sqlite):
    env = _env(db_sqlite, temp_tenant_schema='foo',
               call_kwargs={'dbenv_tenant_schema': 'baz'})
    assert env['tenant_schema'] == 'baz'
