"""The validations of the login forms are LoginComponent methods.

The new-user and new-password forms run without a session, so their remote
validations go through LoginComponent instead of app.getRecordCount and the
adm.user table: these tests run both against a real database, built on a
temporary sqlite file as test_notification_audience does.
"""
import importlib.util
import os
import pathlib
import shutil
import tempfile
import types

from gnr.app.gnrapp import GnrApp

LOGIN = pathlib.Path(__file__).parents[1] / 'resources' / 'login.py'


def _login_component():
    spec = importlib.util.spec_from_file_location('adm_login', LOGIN)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.LoginComponent


class TestLoginValidators(object):

    @classmethod
    def setup_class(cls):
        cls.instance_name = os.environ.get('GNR_TESTING_INSTANCE_NAME') or 'gnrdevelop'
        cls.temp_dir = tempfile.mkdtemp(prefix='gnr_login_validators_')
        cls.app = GnrApp(cls.instance_name, db_attrs=dict(
            implementation='sqlite',
            dbname=os.path.join(cls.temp_dir, 'testing')))
        cls.db = cls.app.db
        cls.db.model.check(applyChanges=True)
        tbl = cls.db.table('adm.user')
        tbl.insert(tbl.newrecord(username='taken_user', email='taken@test.local',
                                 firstname='Taken', lastname='User'))
        cls.db.commit()
        component = _login_component()
        page = types.SimpleNamespace(db=cls.db)
        cls.checkNodupUsername = types.MethodType(component.login_checkNodupUsername, page)
        cls.validateNewPassword = types.MethodType(component.login_validateNewPassword, page)

    @classmethod
    def teardown_class(cls):
        cls.db.closeConnection()
        shutil.rmtree(cls.temp_dir, ignore_errors=True)

    def test_existing_username_is_rejected(self):
        assert self.checkNodupUsername(value='taken_user')['errorcode']

    def test_free_username_is_accepted(self):
        assert self.checkNodupUsername(value='free_user') is True

    def test_empty_password_is_rejected(self):
        assert self.validateNewPassword(value='')['errorcode']

    def test_password_is_accepted(self):
        assert self.validateNewPassword(value='a-new-password') is True
