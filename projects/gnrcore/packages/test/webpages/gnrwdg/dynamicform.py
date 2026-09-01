# -*- coding: utf-8 -*-

"""DynamicForm pane: formbuilder (default) vs formlet backend

The dynamic form pane is normally laid out by ``formbuilder``, which resolves to
the HTML table backend unless the site preference ``theme.use_formlets`` or
``pageOptions['useFormlet']`` is on. ``df_formlet=True`` asks for the CSS grid
backend for that pane alone, whatever the global switch says.

The flag travels through the whole family, so a relation based pane asks for it
the same way::

    pane.dynamicFieldsPane('details', df_formlet=True)

These cases feed ``dynamicFormGroup`` / ``dynamicFormPage`` directly with field
rows in the shape ``GnrDboTable.df_getFieldsRows`` returns, so they need no
dynamic form table to run.
"""

from gnr.core.gnrbag import Bag


def dynamicFields(paged=False):
    """Field rows as df_getFieldsRows returns them.

    Exercised here: mandatory (validate_notnull), validate_range
    (validate_min/max), colspan, field_visible (conditional hidden), formula
    (dataFormula) and a boolean widget.
    """
    fields = [
        dict(code='colore', description='Colore', data_type='T',
             wdg_tag='filteringselect', source_filteringselect='r:Rosso,v:Verde',
             mandatory=True),
        dict(code='taglia', description='Taglia', data_type='L',
             wdg_tag='numbertextbox', validate_range='1:60'),
        dict(code='qta', description='Quantita', data_type='L',
             wdg_tag='numbertextbox'),
        dict(code='note', description='Note', data_type='T',
             wdg_tag='simpletextarea', wdg_kwargs=Bag(dict(colspan=3, height=60))),
        dict(code='garanzia', description='Garanzia mesi', data_type='L',
             wdg_tag='numbertextbox', field_visible='colore=="r"'),
        dict(code='totale', description='Totale', data_type='N',
             wdg_tag='numbertextbox', formula='(taglia||0)*(qta||0)'),
        dict(code='omaggio', description='Omaggio', data_type='B',
             wdg_tag='checkbox'),
    ]
    if paged:
        for r in fields:
            if r['code'] in ('garanzia', 'omaggio', 'totale'):
                r['page'] = 'Extra'
    return fields


class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                    gnrcomponents/dynamicform/dynamicform:DynamicForm"""

    def _dfColumn(self, parent, title, code, df_formlet=None, paged=False):
        col = parent.div(datapath='.%s' % code, border='1px solid #ccc', rounded=6,
                         padding='10px', background='#fafafa')
        col.div(title, font_weight='bold', color='#036', margin_bottom='8px')
        fields = dynamicFields(paged=paged)
        if paged:
            # the tabContainer dynamicFormPage builds is a layout widget: it needs a
            # sized region, in a plain div it collapses to zero height
            recbox = col.borderContainer(height='330px').contentPane(region='center',
                                                                     datapath='.rec')
            recbox.dynamicFormPage(fields=fields, ncol=3, df_formlet=df_formlet)
        else:
            recbox = col.div(datapath='.rec')
            recbox.dynamicFormGroup(fields=fields, ncol=3, df_formlet=df_formlet)
        col.dataController("SET .fires = (fires||0)+1;",
                           taglia='^.rec.taglia', fires='=.fires')
        col.dataFormula('.dump', 'rec?rec.getFormattedValue():""',
                        rec='^.rec', _delay=200)
        foot = col.div(margin_top='10px', border_top='1px dashed #bbb', padding_top='6px')
        foot.div('dataController fires on taglia', font_size='.8em', color='#666')
        foot.div(innerHTML='^.fires', font_size='1.3em', font_weight='bold', color='#c60')
        foot.div('record bag', font_size='.8em', color='#666', margin_top='6px')
        foot.div(innerHTML='^.dump', font_family='monospace', font_size='.75em',
                 background='white', border='1px solid #eee', padding='4px', min_height='60px')
        return col

    def _checklist(self, pane, *items):
        box = pane.div(margin='10px', padding='10px', background='#fffbea',
                       border='1px solid #ffc107', rounded=4, font_size='.85em')
        for item in items:
            box.div(item, margin_bottom='3px')

    def test_0_formbuilder_vs_formlet(self, pane):
        """Same field set, both backends, side by side

        The left pane is the default path (formbuilder, HTML table), the right one
        passes df_formlet=True. Type the same values in both and compare the record
        bag and the fire counter under each column: they must match.
        """
        self._checklist(
            pane,
            'colspan: "Note" declares colspan=3 and must span the whole row on both sides.',
            'hidden: "Garanzia mesi" appears only when Colore is Rosso (field_visible).',
            'dataController: the counter under each column increments on the same Taglia change.',
            'dataFormula: "Totale" is Taglia x Quantita and is read only on both sides.',
            'validation: Colore is mandatory, Taglia is rejected outside 1:60.',
            'save payload: the two record bags must be identical for the same input.')
        box = pane.gridbox(columns=2, gap='15px', margin='10px')
        self._dfColumn(box, 'Default: formbuilder', 'fb')
        self._dfColumn(box, 'df_formlet=True: formlet', 'fl', df_formlet=True)

    def test_1_default_path_regression(self, pane):
        """Default path, pages split over tabs

        Same chain th_product reaches through dynamicFieldsPane: remoteDynamicForm
        feeds dynamicFormPage, which splits the rows by their page and builds a
        formbuilder group per tab. Nothing here passes df_formlet, so this is the
        untouched behaviour.
        """
        self._checklist(
            pane,
            'Two tabs, Main and Extra, each one a formbuilder table.',
            '"Garanzia mesi", "Omaggio" and "Totale" moved to the Extra tab.',
            'Conditional hidden still works across tabs: set Colore to Rosso on Main.',
            '"Totale" sits on Extra and its operands on Main: the formula must '
            'resolve there too, not render "error".')
        box = pane.gridbox(columns=1, margin='10px', max_width='620px')
        self._dfColumn(box, 'Default: formbuilder, paged', 'fbp', paged=True)

    def test_2_formlet_multipage(self, pane):
        """Formlet path, pages split over tabs

        The flag survives the tabContainer branch of dynamicFormPage: every tab gets
        its own formlet instead of its own table.
        """
        self._checklist(
            pane,
            'Two tabs, Main and Extra, each one a CSS grid formlet.',
            'Same tabs, same fields and same validation as test_1.')
        box = pane.gridbox(columns=1, margin='10px', max_width='620px')
        self._dfColumn(box, 'df_formlet=True: formlet, paged', 'flp',
                       df_formlet=True, paged=True)
