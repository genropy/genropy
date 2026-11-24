"""login_createNewUser against a real database.

It runs only when the ``new_user`` login preference is on, and it inserts
only the fields of the new-user form, whatever else the client sends.

The tests build a throwaway application on a temporary sqlite file, as
test_notification_audience does. No mail service is configured, so the
invitation fails after the insert and nothing is committed: the row is read
back inside the same transaction and rolled back.
"""
import importlib.util
import os
import pathlib
import shutil
import tempfile
import types

from gnr.app.gnrapp import GnrApp
from gnr.core.gnrbag import Bag

LOGIN = pathlib.Path(__file__).parents[1] / 'resources' / 'login.py'


def _login_component():
    spec = importlib.util.spec_from_file_location('adm_login', LOGIN)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.LoginComponent


class TestLoginNewUser(object):

    @classmethod
    def setup_class(cls):
        cls.instance_name = os.environ.get('GNR_TESTING_INSTANCE_NAME') or 'gnrdevelop'
        cls.temp_dir = tempfile.mkdtemp(prefix='gnr_login_new_user_')
        cls.app = GnrApp(cls.instance_name, db_attrs=dict(
            implementation='sqlite',
            dbname=os.path.join(cls.temp_dir, 'testing')))
        cls.db = cls.app.db
        cls.db.model.check(applyChanges=True)
        cls.component = _login_component()

    @classmethod
    def teardown_class(cls):
        cls.db.closeConnection()
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def teardown_method(self, method):
        self.db.rollback()

    def _create(self, data, new_user=True):
        page = types.SimpleNamespace(db=self.db, _loginPreference=Bag(dict(new_user=new_user)))
        page.loginPreference = types.MethodType(self.component.loginPreference, page)
        page._immediate_message_parameters = types.MethodType(
            self.component._immediate_message_parameters, page)
        page.login_newUserFields = types.MethodType(self.component.login_newUserFields, page)
        return types.MethodType(self.component.login_createNewUser, page)(
            data=Bag(data) if data is not None else None)

    def _user(self, username):
        rows = self.db.table('adm.user').query(
            columns='$username,$status,$auth_tags,$group_code,$md5pwd',
            where='$username=:u', u=username).fetch()
        return rows[0] if rows else None

    def test_refused_when_new_users_are_off(self):
        result = self._create(dict(firstname='Off', lastname='User', email='off@test.local',
                                   username='nu_off'), new_user=False)
        assert result['error']
        assert self._user('nu_off') is None

    def test_missing_data_is_refused(self):
        assert self._create(None)['error']

    def test_only_form_fields_are_inserted(self):
        self._create(dict(firstname='Mal', lastname='Lory', email='mal@test.local',
                          username='nu_extra', auth_tags='admin,superadmin',
                          group_code='ADMIN', md5pwd='known', status='conf'))
        user = self._user('nu_extra')
        assert user is not None
        assert user['status'] == 'new'
        assert not user['auth_tags']
        assert not user['group_code']
        assert user['md5pwd'] != 'known'
