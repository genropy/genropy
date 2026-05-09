"""Quick Budget Editor — Step 1: 2 levels of nested groupletGrid only.

Building the demo incrementally:
  Step 1 (this file): chapters → accounts (2 levels, no details, no
                      cumulative totals, no footer reactivity).
  Step 2 (next):      add the inner details groupletGrid inside each
                      account.
  Step 3 (next):      cascade tot_netto upwards via dataFormulae.
  Step 4 (next):      visual polish (topbar, toolbar, source banner).
"""
from gnr.core.gnrbag import Bag


class GnrCustomWebPage(object):

    py_requires = ('gnrcomponents/grouplet/grouplet:GroupletHandler,'
                   'gnrcomponents/grouplet/grouplet:GroupletGridHandler')
    css_requires = 'budget_editor/editor_budget'

    def main(self, root, **kwargs):
        # Workaround: wrap in a child pane with explicit datapath so the
        # inner groupletGrid can resolve relative paths during the
        # initial build pass. The proper fix (let gr_groupletGrid honor
        # `datapath` as a canonical kwarg) is deferred to a dedicated
        # phase — first attempt at the widget broke regression tests.
        page = root.contentPane(datapath='budget')
        page.data('.chapters', self._build_fixture())
        page.div('Quick Budget — Step 1 (chapters → accounts)',
                 _class='budget_step_title',
                 font_weight='600', font_size='14px',
                 margin_bottom='4px')
        page.div('3 chapters, each with N accounts. No details yet.',
                 color='#666', font_style='italic',
                 margin_bottom='12px')
        page.groupletGrid(
            storepath='.chapters',
            resource='budget/capitolo_card',
            _class='budget_capitoli_grid',
            addEnabled=True,
            removeEnabled=True,
            dragCode='budget_capitoli',
            defaultRow=dict(codice='', descr=''))

    def _build_fixture(self):
        chapters = Bag()
        chapters.setItem('r_001', self._chapter(
            codice='01', descr='Sopra la linea (ATL)',
            accounts=[
                ('001', 'Diritti soggetto e sceneggiatura'),
                ('002', 'Cast principale'),
                ('003', 'Regista'),
            ]))
        chapters.setItem('r_002', self._chapter(
            codice='02', descr='Cast tecnico (BTL)',
            accounts=[
                ('001', 'Direzione fotografia'),
                ('002', 'Costumi e trucco'),
            ]))
        chapters.setItem('r_003', self._chapter(
            codice='03', descr='Post-produzione',
            accounts=[]))
        return chapters

    def _chapter(self, codice, descr, accounts):
        bag = Bag()
        bag['codice'] = codice
        bag['descr'] = descr
        bag['accounts'] = self._accounts(accounts)
        return bag

    def _accounts(self, account_specs):
        accounts = Bag()
        for i, (codice, descr) in enumerate(account_specs, start=1):
            acc = Bag()
            acc['codice'] = codice
            acc['descr'] = descr
            accounts.setItem(f'r_{i:03d}', acc)
        return accounts
