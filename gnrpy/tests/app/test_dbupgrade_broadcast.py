"""
Tests for the db upgrade lifecycle broadcast (onDbUpgrade -> onDbUpgradeDone).

Resource userobjects are installed by adm.userobject in the onDbUpgradeDone
phase, which fires only after every package completed its own onDbUpgrade
pass: their records may reference rows created by downstream packages during
that pass (issue #1068).
"""
import datetime

from common import BaseGnrAppTest


class TestDbUpgradeBroadcast(BaseGnrAppTest):

    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.app.db.checkDb(applyChanges=True)
        # sys.calendar.onDbUpgrade_createDays bulk-fills the empty table with
        # PostgreSQL-only SQL: seed one row so its early-return keeps the
        # broadcast portable on sqlite
        cls.app.db.table('sys.calendar').insert({'date': datetime.date(2026, 1, 1)})
        cls.app.db.commit()

    def installed_userobjects(self):
        # day_cal is the resource userobject shipped by the sys package
        return self.app.db.table('adm.userobject').query(
            where='$code = :c AND $tbl = :t', c='day_cal', t='sys.calendar').count()

    def test_resource_userobjects_install_in_done_phase(self):
        assert self.installed_userobjects() == 0
        self.app.pkgBroadcast('onDbUpgrade,onDbUpgrade_*')
        # not installed during the upgrade phase: records may reference rows
        # that other packages have not created yet (issue #1068)
        assert self.installed_userobjects() == 0
        self.app.pkgBroadcast('onDbUpgradeDone,onDbUpgradeDone_*')
        assert self.installed_userobjects() == 1

    def test_db_upgrade_broadcast_is_idempotent(self):
        self.app.dbUpgradeBroadcast()
        assert self.installed_userobjects() == 1
        self.app.dbUpgradeBroadcast()
        assert self.installed_userobjects() == 1
