"""Read-only state grid authored through Gramlot."""
from gnr.web.gramlotpage import GramlotPage
from gramlot.grid import GridStruct
from gramlot.page import endpoint


class GnrCustomWebPage(GramlotPage):
    public = True
    title = 'States'

    def main(self, root):
        root.h2('States')
        root.button('Reload', fire='reload')
        root.rpcStore(self.load_states, storeCode='states', storepath='rows',
                      _identifier='code', _onStart=True, _fired='^reload')
        struct = GridStruct()
        cells = struct.view().rows()
        cells.cell('code', name='Code', width=90)
        cells.cell('name', name='State', width=260)
        cells.cell('region_code', name='Region', width=120)
        root.data('struct', struct)
        root.grid(store='states', structpath='struct', height='350px',
                  selectedKey='^selected_state')
        root.p('^selected_state', mask='Selected state: %s')

    @endpoint
    def load_states(self):
        rows = self.db.table('invc.state').query(
            columns='$code,$name,$region_code', order_by='$name').fetch()
        return dict(rows=[dict(row) for row in rows], identifier='code',
                    metadata={'totalrows': len(rows)})
