"""DB-backed form resource for `glbl.regione` used by the groupletGrid
demo page 12. Mixed on top of the upstream `gnr_it.glbl.th_regione`.

The form edits the regione record AND its child provinces in one
panel. Province rows travel through the recordCluster under a
transient `_province_rows` field (`_sendback=True`), exactly like
`erpy_fatt.cl_ordine` ships `_righe_documento`.

Lifecycle:

  - th_onLoading: query glbl.provincia where $regione=:reg →
    selection().output('baglist') → record.setItem('_province_rows',
    bag, _sendback=True).
  - th_onSaving: pop '_province_rows' from the recordCluster so the
    base store does not try to write it as a column. Return it as a
    kwarg for th_onSaved.
  - th_onSaved: walk the bag (digest('#v,#a._pkey,#a._newrecord')),
    insert new rows, update existing ones, delete rows no longer
    present.
"""
from gnr.core.gnrdecorator import public_method
from gnr.web.gnrbaseclasses import BaseComponent


class RegionWithProvinces(BaseComponent):
    def th_form(self, form):
        bc = form.center.borderContainer()
        top = bc.contentPane(region='top', datapath='.record',
                             margin='10px')
        fb = top.formbuilder(cols=2, border_spacing='6px',
                             colswidth='auto', fld_width='100%')
        fb.field('sigla', width='4em', readOnly=True)
        fb.field('nome', width='20em')
        fb.field('codice_istat', width='6em')
        fb.field('zona', width='10em')

        body = bc.contentPane(region='center', datapath='.record',
                              padding='10px', overflow='auto')
        body.div('Province', font_weight='bold',
                 margin_bottom='6px', color='#444')
        body.groupletGrid(storepath='._province_rows',
                          resource='province_row',
                          defaultRow=dict(sigla=None, nome=None,
                                          codice_istat=None),
                          emptyMessage='!!No province yet. '
                                       'Click + to add one.',
                          additem_label='!!Add province')

    def th_options(self):
        return dict(modal=True)

    @public_method
    def th_onLoading(self, record, newrecord, loadingParameters, recInfo):
        if newrecord:
            return
        province_rows = self.db.table('glbl.provincia').query(
            where='$regione=:reg', reg=record['sigla'],
            bagFields=True, columns='*',
            order_by='$nome').selection().output('baglist')
        record.setItem('_province_rows', province_rows, _sendback=True)

    @public_method
    def th_onSaving(self, recordCluster, recordClusterAttr, resultAttr):
        # Pop the transient detail bag off the cluster so the base
        # record store does not try to write it as a column on the
        # master record. Forward it to th_onSaved as a kwarg.
        province_rows = recordCluster.pop('_province_rows', None)
        return dict(province_rows=province_rows)

    @public_method
    def th_onSaved(self, record, resultAttr, province_rows=None, **kwargs):
        # Master-detail save, straight copy of the erpy
        # `cl_ordine.th_onSaved` recipe:
        #   1) snapshot existing children indexed by pkey
        #   2) walk the incoming bag: insert new rows, update the rest
        #   3) whatever pkeys remain in the snapshot were dropped → delete
        if province_rows is None:
            return
        tbl = self.db.table('glbl.provincia')
        regione_sigla = record['sigla']
        existing = tbl.query(where='$regione=:reg',
                             reg=regione_sigla).fetchAsDict('sigla')
        for row, pkey, newrecord in province_rows.digest(
                '#v,#a._pkey,#a._newrecord'):
            row['regione'] = regione_sigla
            if newrecord:
                tbl.insert(row)
            else:
                existing.pop(pkey, None)
                with tbl.recordToUpdate(pkey=pkey) as rec:
                    rec.update(row)
        for stale in existing.values():
            tbl.delete(stale)
