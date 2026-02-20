"""Test for the db_attrs parameter in GnrApp.init().

db_attrs overrides db connection attributes from instanceconfig,
replacing the old forTesting boolean flag.
"""

import os
import tempfile
import warnings

from gnr.app.gnrapp import GnrApp
from tests.core.common import BaseGnrTest


class TestDbAttrs(BaseGnrTest):
    """GnrApp(db_attrs=...) must override instanceconfig db settings."""

    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.tempdir = tempfile.mkdtemp()
        cls.db_attrs = dict(
            implementation='sqlite',
            dbname=os.path.join(cls.tempdir, 'test_db_attrs'),
        )

    def test_db_created_with_db_attrs(self):
        app = GnrApp('test_invoice', db_attrs=self.db_attrs)
        assert app.db is not None

    def test_tables_created(self):
        app = GnrApp('test_invoice', db_attrs=self.db_attrs)
        tbl = app.db.table('invc.customer')
        count = tbl.query().count()
        assert count == 0

    def test_insert_and_query(self):
        app = GnrApp('test_invoice', db_attrs=self.db_attrs)
        tbl = app.db.table('invc.customer')
        tbl.insert(dict(account_name='DbAttrs Test'))
        app.db.commit()
        count = tbl.query().count()
        assert count >= 1

    def test_implementation_override(self):
        app = GnrApp('test_invoice', db_attrs=self.db_attrs)
        assert app.db.implementation == 'sqlite'


class TestForTestingDeprecation(BaseGnrTest):
    """forTesting=True must emit DeprecationWarning and still work."""

    @classmethod
    def setup_class(cls):
        super().setup_class()

    def test_deprecation_warning_emitted(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            app = GnrApp('test_invoice', forTesting=True)
            deprecation = [x for x in w if issubclass(x.category, DeprecationWarning)]
            assert len(deprecation) > 0, 'forTesting must emit DeprecationWarning'
            assert 'deprecated' in str(deprecation[0].message).lower()

    def test_for_testing_still_creates_db(self):
        with warnings.catch_warnings(record=True):
            warnings.simplefilter('always')
            app = GnrApp('test_invoice', forTesting=True)
            assert app.db is not None
            tbl = app.db.table('invc.customer')
            count = tbl.query().count()
            assert count == 0
