"""Real checks on the xlsx table importer (#797).

The rows go through a real ``XlsxReader`` over a real file and through
``GnrWebUtils.defaultMatchImporterXls`` on the ``gnrtest`` instance, so the
assertions look at the records the import actually left in the database.

``adm.ckstyle`` is the fixture table: its pkey is a generated uuid and it has
neither counters nor hierarchy, so ``name`` can play the part of the business
column the user ticks as key in the match grid -- the case where the importer
used to overwrite the pkey of every record it updated.
"""

import os
import tempfile

import openpyxl

from core.common import BaseGnrTest

from gnr.app.gnrapp import GnrApp
from gnr.core.flatfiles import getReader
from gnr.web.gnrdummysite import GnrDummySite

TABLE = 'adm.ckstyle'
KEY_MATCH = {'name': 'name', 'styles': 'styles', '_updater_keyfield': 'name'}


def _write_xlsx(rows):
    """Write *rows* to a temp xlsx and return its path, to be removed by the caller"""
    wb = openpyxl.Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
        path = f.name
    wb.save(path)
    return path


class TestDefaultMatchImporterXls(BaseGnrTest):

    @classmethod
    def setup_class(cls):
        super().setup_class()
        app = GnrApp(cls.test_instance_name)
        app.db.model.check(applyChanges=True)
        app.db.commit()
        cls.site = GnrDummySite(cls.test_instance_name, site_name=cls.test_instance_name)
        cls.db = cls.site.db
        cls.tblobj = cls.db.table(TABLE)
        cls.page = cls.site.dummyPage

    def setup_method(self):
        """Start every test from a table holding one known record"""
        self.tblobj.empty()
        self.record = self.tblobj.newrecord(name='S1', styles='color:red')
        self.tblobj.insert(self.record)
        self.db.commit()

    def runImport(self, rows, match_index=None, **kwargs):
        """Import *rows* through a real xlsx file, as tableImporterRun does"""
        path = _write_xlsx(rows)
        try:
            reader = getReader(path)
            return self.page.utils.defaultMatchImporterXls(tblobj=self.tblobj, reader=reader,
                                                           match_index=dict(match_index),
                                                           **kwargs)
        finally:
            os.unlink(path)

    def styleByName(self, name):
        return self.tblobj.record(name=name, ignoreMissing=True).output('dict')

    def test_update_only_sql_mode_keeps_the_pkey(self):
        """update_only must not renumber the records it updates (#797).

        With sql_mode the rows used to get a generated pkey, which raw_update
        then wrote over the pkey of the record it was updating, as
        SET id=<generated> WHERE id=<current>: the update landed, but every
        fkey pointing at that record was left orphaned.
        """
        result = self.runImport([['name', 'styles'], ['S1', 'color:green']],
                                match_index=KEY_MATCH,
                                import_mode='update_only', sql_mode=True)
        assert result == 'OK'
        record = self.styleByName('S1')
        assert record['id'] == self.record['id']
        assert record['styles'] == 'color:green'
        assert self.tblobj.query().count() == 1

    def test_update_only_updates_by_business_key(self):
        """The same import without sql_mode goes through the non raw update path"""
        result = self.runImport([['name', 'styles'], ['S1', 'color:green']],
                                match_index=KEY_MATCH,
                                import_mode='update_only')
        assert result == 'OK'
        record = self.styleByName('S1')
        assert record['id'] == self.record['id']
        assert record['styles'] == 'color:green'
        assert self.tblobj.query().count() == 1

    def test_update_only_leaves_unknown_keys_out(self):
        """A row whose key matches no record is reported, not inserted"""
        result = self.runImport([['name', 'styles'], ['S9', 'color:green']],
                                match_index=KEY_MATCH,
                                import_mode='update_only', sql_mode=True)
        assert result == 'OK'
        assert not self.styleByName('S9')
        assert self.tblobj.query().count() == 1

    def test_sql_mode_insert_assigns_a_pkey(self):
        """Without update_only, sql_mode still needs the pkey up front for insertMany"""
        result = self.runImport([['name', 'styles'], ['S2', 'color:blue']],
                                match_index=KEY_MATCH, sql_mode=True)
        assert result == 'OK'
        record = self.styleByName('S2')
        assert record['id']
        assert record['styles'] == 'color:blue'
        assert self.tblobj.query().count() == 2

    def test_updater_keyfield_is_never_read_as_a_column(self):
        """_updater_keyfield is client metadata (#797).

        The insert paths do not pop it from match_index, so looking it up in the
        row -- there is no column of that name -- used to raise KeyError.
        """
        result = self.runImport([['name', 'styles'], ['S3', 'color:black']],
                                match_index=KEY_MATCH)
        assert result == 'OK'
        assert self.styleByName('S3')['styles'] == 'color:black'
