from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    js_requires = 'grouplets/transforms/payment_data'

    def __info__(self):
        return dict(
            caption='Payment Data',
            priority=5,
            onLoading="function(data){payment_data.onLoading(data);}",
            onSaving="function(data, sourceBag){payment_data.onSaving(data, sourceBag);}"
        )

    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2)
        fb.filteringSelect(
            value='^.PaymentTerms',
            values='TP01:Installments,TP02:Full payment,TP03:Advance',
            lbl='Payment Terms',
            colspan=2,
            width='100%'
        )
        pane.bagGrid(
            frameCode='payment_detail',
            storepath='#FORM.record.PaymentDetail',
            struct=self._payment_data_struct,
            datapath='#FORM.grid_payment_detail',
            title='Payment Detail',
            height='200px',
            addrow=True,
            delrow=True
        )

    def _payment_data_struct(self, struct):
        r = struct.view().rows()
        r.cell('PaymentMethod', name='Method',
               width='15em',
               edit=dict(tag='filteringSelect',
                         values=','.join([
                             'MP01:Cash',
                             'MP02:Check',
                             'MP05:Bank transfer',
                             'MP08:Credit card',
                             'MP12:RIBA'
                         ])))
        r.cell('PaymentDueDate', name='Due Date',
               width='10em', dtype='D',
               edit=dict(tag='dateTextBox'))
        r.cell('PaymentAmount', name='Amount',
               width='10em', dtype='N',
               edit=True,
               format='###,###,##0.00')
