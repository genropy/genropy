"""Two packages hook a table method of a third one through ``model/_packages`` (#1883).

The three packages live on disk, an instance declares them, and the application
boots on SQLite: the hooks are reached through ``db.table()``, on the real
``SqlTable``, after both mixin hops the boot performs.
"""

import os
import shutil
import tempfile

from gnr.app.gnrapp import GnrApp
from gnr.dev.makers.instance import InstanceMaker

from core.common import BaseGnrTest

PACKAGE_MAIN = """from gnr.app.gnrdbo import GnrDboTable, GnrDboPackage


class Package(GnrDboPackage):
    def config_attributes(self):
        return dict(sqlschema='{pkg}', sqlprefix=True,
                    name_short='{pkg}', name_long='{pkg}', name_full='{pkg}')

    def config_db(self, pkg):
        pass


class Table(GnrDboTable):
    pass
"""

OWNER_TABLE = """from gnr.core.gnrdecorator import customizable


class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('ledger', pkey='id')
        tbl.column('id', size='22')

    @customizable
    def updateBalance(self, amount):
        self.hook_calls.append('owner')
        return amount
"""

HOOK_TABLE = """from gnr.core.gnrdecorator import {decorator}


class Table(object):
    @{decorator}
    def updateBalance(self, amount, **kwargs):
        self.hook_calls.append('{pkg} %s' % kwargs.get('_original_result'))
"""


class TestPackageTableHooks(BaseGnrTest):
    instance_name = 'table_hooks'
    owner = 'hookowner'
    hooks = (('hookfirst', 'oncalling'), ('hooksecond', 'oncalled'))

    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.tempdir = tempfile.mkdtemp()
        cls.packages_path = os.path.join(cls.tempdir, 'packages')
        cls.writePackage(cls.owner, {'model/ledger.py': OWNER_TABLE})
        for pkg, decorator in cls.hooks:
            cls.writePackage(pkg, {
                'model/_packages/%s/ledger.py' % cls.owner:
                    HOOK_TABLE.format(decorator=decorator, pkg=pkg)})
        InstanceMaker(cls.instance_name, base_path=cls.test_instance_path,
                      packages=[(pkg, cls.packages_path)
                                for pkg in [cls.owner] + [p for p, _ in cls.hooks]],
                      authentication=False).do()

    @classmethod
    def teardown_class(cls):
        super().teardown_class()
        shutil.rmtree(cls.tempdir, ignore_errors=True)

    @classmethod
    def writePackage(cls, pkg, files):
        files = dict(files, **{'main.py': PACKAGE_MAIN.format(pkg=pkg)})
        for relpath, source in files.items():
            path = os.path.join(cls.packages_path, pkg, relpath)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as fp:
                fp.write(source)

    def ledger(self):
        app = GnrApp(self.instance_name, db_attrs=dict(
            implementation='sqlite', dbname=os.path.join(self.tempdir, self.instance_name)))
        tbl = app.db.table('%s.ledger' % self.owner)
        tbl.hook_calls = []
        return tbl

    def test_hooks_of_both_packages_run_around_the_owner_method(self):
        tbl = self.ledger()

        assert type(tbl).__name__ == 'SqlTable'
        assert tbl.updateBalance(10) == 10
        assert tbl.hook_calls == ['hookfirst None', 'owner', 'hooksecond 10']

    def test_the_owner_method_is_not_replaced(self):
        tbl = self.ledger()

        assert not hasattr(tbl, 'updateBalance_')
        assert len([k for k in dir(tbl) if k.startswith('updateBalance_oncalling_')]) == 1
        assert len([k for k in dir(tbl) if k.startswith('updateBalance_oncalled_')]) == 1
