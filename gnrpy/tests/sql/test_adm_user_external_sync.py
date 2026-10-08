"""adm.user.syncExternalUser creates a user that is not in the db yet.

An external authentication service (ldaps) hands over a plain dict with only
the user data, without ``md5pwd`` or ``status`` and with keys that are not
columns: the user must still be inserted as a complete record.
"""
from core.common import BaseGnrTest


def setup_module(module):
    BaseGnrTest.setup_class()


def teardown_module(module):
    BaseGnrTest.teardown_class()


def test_sync_creates_a_new_external_user_without_md5pwd(db_pg):
    db = db_pg
    tbl = db.table('adm.user')
    tbl.syncExternalUser(dict(username='ext_new_user', firstname='Ext',
                              lastname='User', email='ext_new_user@example.com',
                              ldap_user=dict(cn='ext_new_user')))
    record = tbl.record(username='ext_new_user').output('dict')
    assert record['firstname'] == 'Ext'
    assert record['email'] == 'ext_new_user@example.com'
    assert not record['md5pwd']
