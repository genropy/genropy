"""Native Bag row deletion and attribute changes through a database form."""

from gnr.core.gnrbag import Bag


class GnrCustomWebPage(object):
    py_requires = (
        'gnrcomponents/testhandler:TestHandlerFull,'
        'gnrcomponents/formhandler:FormHandler,'
        'gnrcomponents/grouplet/grouplet:GroupletGridHandler'
    )

    def test_1_record_bag(self, pane):
        """Save the fixture, delete a row, Save and Reload; repeat for its last row.

        Set first row unit checks attribute-only changes. Inspect changes shows
        the live Bag and fields submitted by the ordinary recordCluster store.
        """
        payload = Bag()
        payload.setItem('rows.keep', Bag(dict(product='Keep row', qty=2,
                                             price=12.5, note='Keep this note')),
                        unit='kg', code='K')
        payload.setItem('rows.keep.hidden', Bag(dict(reference='preserve-me')))
        payload.setItem('rows.remove', Bag(dict(product='Delete row', qty=1,
                                               price=3.25)), unit='kg', code='R')
        payload.setItem('metadata', Bag(dict(version=1)), source='fixture')
        pane.data('bag_persistence_seed', payload)
        form = pane.frameForm(frameCode='bag_persistence', datapath='.form',
                              formId='bag_persistence_form',
                              height='620px', border='1px solid silver')
        store = form.formStore(table='test.myticket', storeType='Item',
                               handler='recordCluster', startKey='*newrecord*',
                               onSaved='reload')
        store.handler('load', default_subject='REGRESSION-1608-direct',
                      default_extra_data='=bag_persistence_seed')
        bar = form.top.slotToolbar(
            '5,selector,reload,inspect,unit,setunit,*,semaphore,locker,formcommands,5')
        bar.selector.dbSelect(value='^.fixture_id', dbtable='test.myticket',
                              parentForm=False, width='16em', hasDownArrow=True,
                              condition='$subject LIKE :prefix',
                              condition_prefix='REGRESSION-1608%',
                              validate_onAccept="""if(userChange){
                                  genro.formById('bag_persistence_form').load({destPkey:value});
                              }""")
        bar.reload.slotButton('Reload', action="""
            this.form.publish('load', {destPkey:this.form.getCurrentPkey()});
        """)
        bar.inspect.slotButton('Inspect changes', action="""
            var form = this.form;
            var payload = form.getFormData().getItem('extra_data');
            var rows = payload && payload.getItem('rows');
            var changes = form.getFormChanges().getItem('record');
            form.sourceNode.setRelativeData('.verification', JSON.stringify({
                pkey: form.getCurrentPkey(), dirty: form.hasChanges(),
                submitted: changes.keys(),
                rows: rows ? rows.getNodes().map(function(n){
                    return {key:n.label, product:n.getValue().getItem('product'),
                            unit:n.attr.unit, code:n.attr.code};
                }) : []
            }, null, 2));
        """)
        bar.unit.textbox(value='^#FORM.unit', width='5em', placeholder='Unit')
        bar.setunit.slotButton('Set first row unit', action="""
            var rows = this.form.getFormData().getItem('extra_data.rows');
            var first = rows && rows.getNodes()[0];
            if(first) this.setRelativeData(
                '#FORM.record.extra_data.rows.' + first.label + '?unit', unit);
        """, unit='=#FORM.unit')
        center = form.center.contentPane(datapath='.record', padding='10px')
        center.formbuilder(cols=1).field('subject', width='30em')
        center.groupletGrid(storepath='.extra_data.rows',
                            struct=self.row_struct, nodeId='bag_persistence_rows',
                            additem='entry', rowTemplate=True, rowCheckbox=True,
                            delitem=True, selectionmenu=dict(delete=True))
        form.bottom.contentPane(height='180px').simpleTextArea(
            value='^.verification', readOnly=True, width='100%', height='170px')

    def row_struct(self, struct):
        row = struct.view().rows()
        row.cell('product', name='Product', width='16em', edit=True,
                 validate_notnull=True)
        row.cell('qty', name='Qty', dtype='L', width='6em', edit=True)
        row.cell('price', name='Price', dtype='N', width='7em', edit=True)
        row.cell('note', name='Note', width='20em', edit=True)
