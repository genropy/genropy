"""Real checks on the output document naming of TableScriptToHtml.

``sys.batch_log`` is the fixture table: its ``caption_field`` is the formula
column ``log_caption``, the shape that made every record of a table print to
the same file name.
"""

import os
import re

from core.common import BaseGnrTest

from gnr.app.gnrapp import GnrApp
from gnr.web import gnrbaseclasses
from gnr.web.gnrbaseclasses import TableScriptToHtml
from gnr.web.gnrdummysite import GnrDummySite


class NoGridPrint(TableScriptToHtml):
    def gridData(self):
        return []


class FirstPrint(NoGridPrint):
    _gnrPublicName = '_tblscript.sys.batch_log.print/first.Main'


class SecondPrint(NoGridPrint):
    _gnrPublicName = '_tblscript.sys.batch_log.print/second.Main'


class WithVirtualColumns(FirstPrint):
    virtual_columns = 'logfile_url'


class TestTableScriptOutputName(BaseGnrTest):

    @classmethod
    def setup_class(cls):
        super().setup_class()
        app = GnrApp(cls.test_instance_name)
        app.db.model.check(applyChanges=True)
        app.db.commit()
        cls.site = GnrDummySite(cls.test_instance_name, site_name=cls.test_instance_name)
        cls.tblobj = cls.site.db.table('sys.batch_log')
        cls.pkeys = []
        for tbl, title in (('invc.invoice', 'alpha'), ('invc.customer', 'beta')):
            record = cls.tblobj.newrecord(tbl=tbl, batch_title=title)
            cls.tblobj.insert(record)
            cls.pkeys.append(record['id'])
        cls.site.db.commit()

    def buildScript(self, klass, record):
        script = klass(page=self.site.dummyPage, resource_table=self.tblobj)
        script(record=record)
        return script

    def test_module_under_test(self):
        # the editable install resolves gnr.* to the main checkout, so make sure
        # the module being exercised is the one in this working tree
        checkout = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        assert gnrbaseclasses.__file__.startswith(checkout + os.sep)

    def test_caption_virtual_columns_are_loaded(self):
        script = self.buildScript(FirstPrint, self.pkeys[0])
        assert script.captionVirtualColumns() == 'log_caption'
        assert script.record['log_caption'] == 'invc.invoicealpha'

    def test_declared_virtual_columns_are_kept(self):
        script = WithVirtualColumns(page=self.site.dummyPage, resource_table=self.tblobj)
        assert script.captionVirtualColumns().split(',') == ['logfile_url', 'log_caption']

    def test_caption_is_the_record_not_the_table_name(self):
        name = os.path.basename(self.buildScript(FirstPrint, self.pkeys[0]).filepath)
        assert 'invcinvoicealpha' in name

    def test_name_is_record_specific(self):
        names = []
        for pkey in self.pkeys:
            name = os.path.basename(self.buildScript(FirstPrint, pkey).filepath)
            assert name.endswith('%s.html' % re.sub(r'\W', '_', pkey))
            names.append(name)
        assert len(set(names)) == len(self.pkeys)

    def test_name_is_resource_specific(self):
        pkey = self.pkeys[0]
        assert self.buildScript(FirstPrint, pkey).filepath != self.buildScript(SecondPrint, pkey).filepath

    def test_pkeyless_prints_never_share_a_file(self):
        first = self.buildScript(FirstPrint, '*').filepath
        second = self.buildScript(FirstPrint, '*').filepath
        assert first != second

    def test_a_bag_record_keeps_what_the_caller_merged_in(self):
        # btcprint and print_template pass a Bag already loaded with the batch's
        # own virtual_columns and extra keys merged in; asking recordAs for the
        # caption columns would reload it from the database and drop both
        record = self.tblobj.record(pkey=self.pkeys[0], mode='bag')
        record['batch_parameter'] = 'kept'
        script = self.buildScript(FirstPrint, record)
        assert script.record['batch_parameter'] == 'kept'

    def test_a_bag_record_still_prints_to_its_own_file(self):
        names = []
        for pkey in self.pkeys:
            record = self.tblobj.record(pkey=pkey, mode='bag')
            names.append(os.path.basename(self.buildScript(FirstPrint, record).filepath))
        assert len(set(names)) == len(self.pkeys)
        for pkey, name in zip(self.pkeys, names):
            assert name.endswith('%s.html' % re.sub(r'\W', '_', pkey))
