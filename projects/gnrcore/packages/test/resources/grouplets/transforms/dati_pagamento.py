from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    js_requires = 'grouplets/transforms/dati_pagamento'

    def __info__(self):
        return dict(
            caption='Dati Pagamento',
            priority=5,
            onLoading="function(data){dati_pagamento.onLoading(data);}",
            onSaving="function(data, sourceBag){dati_pagamento.onSaving(data, sourceBag);}"
        )

    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2)
        fb.filteringSelect(
            value='^.CondizioniPagamento',
            values='TP01:Pagamento a rate,TP02:Pagamento completo,TP03:Anticipo',
            lbl='Condizioni Pagamento',
            colspan=2,
            width='100%'
        )
        pane.bagGrid(
            frameCode='dettaglio_pagamento',
            storepath='#FORM.record.DettaglioPagamento',
            struct=self._dati_pagamento_struct,
            datapath='#FORM.grid_dettaglio_pagamento',
            title='Dettaglio Pagamento',
            height='200px',
            addrow=True,
            delrow=True
        )

    def _dati_pagamento_struct(self, struct):
        r = struct.view().rows()
        r.cell('ModalitaPagamento', name='Modalita',
               width='15em',
               edit=dict(tag='filteringSelect',
                         values=','.join([
                             'MP01:Contanti',
                             'MP02:Assegno',
                             'MP05:Bonifico',
                             'MP08:Carta di pagamento',
                             'MP12:RIBA'
                         ])))
        r.cell('DataScadenzaPagamento', name='Data Scadenza',
               width='10em', dtype='D',
               edit=dict(tag='dateTextBox'))
        r.cell('ImportoPagamento', name='Importo',
               width='10em', dtype='N',
               edit=True,
               format='###,###,##0.00')
