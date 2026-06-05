"""Test for the db_attrs parameter in GnrApp.init().

db_attrs overrides db connection attributes from instanceconfig.
"""

import os
import tempfile
import shutil

from gnr.app.gnrapp import GnrApp
from core.common import BaseGnrTest


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
        
    @classmethod
    def teardown_class(cls):
        super().teardown_class()
        if cls.tempdir and os.path.exists(cls.tempdir):
            shutil.rmtree(cls.tempdir)
            
    def test_db_created_with_db_attrs(self):
        app = GnrApp('test_invoice', db_attrs=self.db_attrs)
        assert app.db is not None

    def test_tables_created(self):
        app = GnrApp('test_invoice', db_attrs=self.db_attrs)
        app.db.model.check(applyChanges=True)
        tbl = app.db.table('invc.customer')
        count = tbl.query().count()
        assert count == 0

    def test_insert_and_query(self):
        app = GnrApp('test_invoice', db_attrs=self.db_attrs)
        app.db.model.check(applyChanges=True)
        tbl = app.db.table('invc.customer')
        tbl.insert(dict(account_name='DbAttrs Test'))
        app.db.commit()
        count = tbl.query().count()
        assert count >= 1

    def test_implementation_override(self):
        app = GnrApp('test_invoice', db_attrs=self.db_attrs)
        assert app.db.implementation == 'sqlite'
