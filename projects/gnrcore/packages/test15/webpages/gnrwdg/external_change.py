# -*- coding: utf-8 -*-

"""setInClientRecord: a silent server push must not stage a change"""

from gnr.core.gnrdecorator import public_method


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull,gnrcomponents/formhandler:FormHandler"

    def test_0_silent_push(self, pane):
        """Push twice, then save: no pushed field may reach the changeSet.

        numero_abitanti is a formulaColumn loaded with the record. Before the fix
        the first push wiped the node attributes (dtype, virtual_column) and the
        second push, same value, left _loadedValue on it: the save then raised
        'Incompatible changes: another user modified field numero_abitanti'.
        Expected now: the form stays unchanged after both pushes and the save
        has nothing to send."""
        form = pane.frameForm(frameCode='prov_push', datapath='.form',
                              height='160px', width='600px', border='1px solid silver')
        store = form.formStore(table='glbl.provincia', storeType='Item',
                               handler='recordCluster', startKey='MI')
        store.handler('load', virtual_columns='numero_abitanti')
        tb = form.top.slotToolbar('5,pusher,*,semaphore,|,formcommands,5')
        tb.pusher.slotButton('Push totals (silent)').dataRpc(self.pushTotals,
                                                             pkey='=#FORM.record.sigla')
        fb = form.center.contentPane(datapath='.record').formbuilder(cols=2, border_spacing='4px')
        fb.field('nome')
        fb.field('codice')
        fb.numberTextBox(value='^.numero_abitanti', lbl='N.Abitanti (formula)', readOnly=True)

    @public_method
    def pushTotals(self, pkey=None):
        tbl = self.db.table('glbl.provincia')
        with tbl.recordToUpdate(pkey) as record:
            record['codice'] = (record['codice'] or 0) + 1
        self.db.commit()
        record['numero_abitanti'] = tbl.readColumns(columns='$numero_abitanti', pkey=pkey)
        self.setInClientRecord(tblobj=tbl, record=record, fields='codice,numero_abitanti')
