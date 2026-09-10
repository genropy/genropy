"""Server pushes must preserve bindings without staging silent changes."""

from gnr.core.gnrdecorator import public_method


class GnrCustomWebPage(object):
    py_requires = (
        'gnrcomponents/testhandler:TestHandlerFull,'
        'gnrcomponents/formhandler:FormHandler'
    )

    def test_0_silent_push(self, pane):
        """Push loaded and unloaded virtuals, then edit Name and save."""
        pane.div(
            'Silent pushes must leave the form unchanged. '
            'Edit Name before a push: that edit must survive and save. '
            'A non-silent push must mark Code as changed.',
            margin='10px'
        )
        form = pane.frameForm(
            frameCode='prov_push', datapath='.form',
            height='360px', width='1000px', border='1px solid silver'
        )
        store = form.formStore(
            table='glbl.provincia', storeType='Item',
            handler='recordCluster', startKey='MI'
        )
        store.handler('load', virtual_columns='numero_abitanti')
        bar = form.top.slotToolbar(
            '5,loaded,unloaded,tracked,inspect,*,semaphore,|,formcommands,5'
        )
        bar.loaded.slotButton('Push loaded virtual').dataRpc(
            self.pushTotals, pkey='=#FORM.record.sigla',
            virtual_column='numero_abitanti'
        )
        bar.unloaded.slotButton('Push unloaded virtual').dataRpc(
            self.pushTotals, pkey='=#FORM.record.sigla',
            virtual_column='tot_superficie'
        )
        bar.tracked.slotButton('Push non-silent').dataRpc(
            self.pushTotals, pkey='=#FORM.record.sigla', silent=False
        )
        bar.inspect.slotButton('Inspect changes', action="""
            var record = this.form.getFormData();
            var state = {changed:this.form.hasChanges(),
                         changeSet:this.form.getFormChanges().getItem('record').keys(),
                         fields:{}};
            ['codice','numero_abitanti','tot_superficie'].forEach(function(field){
                var node = record.getNode(field);
                state.fields[field] = node?{value:node.getValue(),
                    dtype:node.attr.dtype,virtual_column:node.attr.virtual_column,
                    hasLoadedValue:'_loadedValue' in node.attr}:null;
            });
            this.form.sourceNode.setRelativeData('.verification',JSON.stringify(state,null,2));
        """)
        fb = form.center.contentPane(datapath='.record').formbuilder(
            cols=2, border_spacing='4px'
        )
        fb.field('nome', lbl='Name')
        fb.field('codice', lbl='Code')
        fb.numberTextBox(
            value='^.numero_abitanti', lbl='Population (loaded virtual)',
            readOnly=True
        )
        form.bottom.contentPane(height='170px').simpleTextArea(
            value='^.verification', height='160px', width='100%', readOnly=True
        )

    @public_method
    def pushTotals(self, pkey=None, virtual_column=None, silent=True):
        tbl = self.db.table('glbl.provincia')
        with tbl.recordToUpdate(pkey) as record:
            record['codice'] = (record['codice'] or 0) + 1
        self.db.commit()
        fields = 'codice'
        if virtual_column:
            record[virtual_column] = tbl.readColumns(
                columns=f'${virtual_column}', pkey=pkey
            )
            fields += f',{virtual_column}'
        self.setInClientRecord(
            tblobj=tbl, record=record, fields=fields, silent=silent
        )
