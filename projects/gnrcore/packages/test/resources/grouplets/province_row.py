"""Province editor row — full editable record from `glbl.provincia`.

Used by the DB-backed groupletGrid demo (page 12). Each row carries
the persisted fields of a province (sigla, nome, codice_istat). Inserts
and deletes flow through the groupletGrid; the form resource on the
parent regione handles the actual DB write in `th_onSaved`.
"""
from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Province Row', priority=25)

    def grouplet_main(self, pane, **kwargs):
        row = pane.div(display='flex', gap='8px', align_items='center')
        row.textbox(value='^.sigla', placeholder='!!Sigla',
                    width='4em', validate_notnull=True,
                    validate_case='u', validate_len='2:2',
                    lbl=None)
        row.textbox(value='^.nome', placeholder='!!Name',
                    flex='1 1 auto', validate_notnull=True,
                    lbl=None)
        row.textbox(value='^.codice_istat',
                    placeholder='!!Istat code',
                    width='6em', lbl=None)
