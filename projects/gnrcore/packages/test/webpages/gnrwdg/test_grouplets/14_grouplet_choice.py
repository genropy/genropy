# -*- coding: utf-8 -*-

"""Test page for groupletChoice: choice tiles as a self-advancing wizard step."""

from gnr.core.gnrdecorator import public_method


class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                     gnrcomponents/grouplet/grouplet:GroupletHandler"""

    def test_1_choice_step(self, pane):
        """The Kind step has no Next button (autoNext in its __info__): a click
        on a tile selects it and moves to Details. Back returns to Kind with
        the tile still marked; a click on any tile moves on again."""
        pane.borderContainer(height='420px', border='1px solid silver',
                             datapath='.wizard_choice').groupletWizard(
            topic='wizard_choice', value='^.record',
            frameCode='wizard_choice', stepperPosition='left',
            stepSummary=True, region='center')

    def test_2_choice_alone(self, pane):
        """The same tiles outside a wizard: a click selects, nothing advances."""
        pane.grouplet(value='^.choice_alone', handler=self.grp_choice)
        pane.div('^.choice_alone.kind', margin_top='8px')

    def test_3_choice_from_table(self, pane):
        """Tiles from a query on glbl.regione (zona_numero 1 and 2), one group
        per zone: the value is the pkey, the query parameter a kwarg."""
        pane.grouplet(value='^.choice_table', handler=self.grp_choice_table)
        pane.div('^.choice_table.regione', margin_top='8px')

    @public_method
    def grp_choice(self, pane, **kwargs):
        pane.groupletChoice(field='kind', value_column='code', title='description',
                            rows=[dict(code='A', description='Alpha'),
                                  dict(code='B', description='Beta')])

    @public_method
    def grp_choice_table(self, pane, **kwargs):
        pane.groupletChoice(field='regione', table='glbl.regione',
                            columns='$sigla,$nome,$zona,$zona_numero',
                            where='$zona_numero<=:max_zona', max_zona=2,
                            order_by='$zona_numero,$nome',
                            glyph='sigla', title='nome', note='Zone $zona',
                            groups=[dict(caption=f'Zone {n}',
                                         condition=lambda r, n=n: r['zona_numero'] == n)
                                    for n in (1, 2)])
