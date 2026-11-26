# -*- coding: utf-8 -*-

"""Bag.diff and Bag.getDiffBag between two versions of a Bag"""

import datetime
from decimal import Decimal

from gnr.core.gnrdecorator import public_method
from gnr.core.gnrbag import Bag


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_0_clinical_record(self, pane):
        "Changed, added and removed values and a changed attribute in a synthetic clinical record"
        old = Bag()
        old['gravidanza.UM'] = datetime.date(2026, 3, 1)
        old['gravidanza.LivelloRischio'] = '2'
        old['misure.Peso'] = 62.5
        old.setItem('misure.Altezza', 165, unit='cm')
        new = old.deepcopy()
        new['gravidanza.LivelloRischio'] = '3'
        new['gravidanza.ModalitaParto'] = 'cesareo'
        new.pop('misure.Peso')
        new.setAttr('misure.Altezza', unit='mm')
        new.setItem('ecografia', Bag(dict(settimana=12, esito='regolare')), operatore='A1')
        self._diffLayout(pane, old, new)

    def test_1_duplicated_labels(self, pane):
        "Siblings with the same label are matched by order of appearance; their paths use #n"
        old = Bag()
        old['visite'] = Bag()
        old['visite'].addItem('visita', Bag(dict(esito='ok')), data=datetime.date(2026, 4, 1))
        old['visite'].addItem('visita', Bag(dict(esito='controllo')), data=datetime.date(2026, 5, 1))
        new = old.deepcopy()
        new['visite.#1.esito'] = 'ricovero'
        new['visite'].addItem('visita', Bag(dict(esito='ok')), data=datetime.date(2026, 6, 1))
        self._diffLayout(pane, old, new)

    def test_2_types_and_attributes(self, pane):
        "Values keep their type: '2' and 2 differ; attributes are compared one by one"
        old = Bag()
        old['codice'] = '2'
        old['importo'] = Decimal('10.50')
        old.setItem('pressione', 120, unit='mmHg', metodo='manuale')
        old['misure'] = Bag(dict(peso=60))
        new = Bag()
        new['codice'] = 2
        new['importo'] = Decimal('10.5')
        new.setItem('pressione', 120, unit='mmHg', strumento='digitale')
        new['misure'] = 'non rilevate'
        self._diffLayout(pane, old, new)

    def _diffLayout(self, pane, old, new):
        pane.data('.old', old.toXml())
        pane.data('.new', new.toXml())
        bc = pane.borderContainer(height='640px', width='100%')
        top = bc.borderContainer(region='top', height='240px', splitter=True)
        top.contentPane(region='left', width='50%', splitter=True, padding='4px').simpleTextArea(
            value='^.old', height='100%', width='100%', font_family='monospace', font_size='.8em')
        top.contentPane(region='center', padding='4px').simpleTextArea(
            value='^.new', height='100%', width='100%', font_family='monospace', font_size='.8em')
        bc.dataRpc('.result', self.bagDiff, old='^.old', new='^.new', _onStart=True)
        center = bc.borderContainer(region='center')
        grid = center.contentPane(region='center').quickGrid(value='^.result.records',
                                                             height='100%', width='100%')
        grid.column('event', name='Event', width='6em')
        grid.column('path', name='Path', width='16em')
        grid.column('changed_attribute', name='Attribute', width='7em')
        grid.column('oldvalue', name='Old value', width='12em')
        grid.column('newvalue', name='New value', width='12em')
        center.contentPane(region='right', width='40%', splitter=True, overflow='auto',
                           padding='4px').tree(storepath='.result.tree', hideValues=True,
                                               labelAttribute='caption', font_size='.85em')

    @public_method
    def bagDiff(self, old=None, new=None, **kwargs):
        old = Bag(old) if old else Bag()
        new = Bag(new) if new else Bag()
        records = Bag()
        for k, record in enumerate(old.diff(new)):
            records.setItem('r_%i' % k, None, event=record['event'], path=record['path'],
                            changed_attribute=record['changed_attribute'],
                            oldvalue=self._shownValue(record['oldvalue']),
                            newvalue=self._shownValue(record['newvalue']))
        tree = old.getDiffBag(new)
        tree.walk(self._setCaption)
        return Bag(dict(records=records, tree=tree))

    def _setCaption(self, node, **kwargs):
        attr = node.attr
        caption = node.label
        event = attr.get('event')
        if event == 'added' and 'newvalue' in attr:
            caption = '%s: added %s' % (caption, self._shownValue(attr['newvalue']))
        elif event == 'removed' and 'oldvalue' in attr:
            caption = '%s: removed %s' % (caption, self._shownValue(attr['oldvalue']))
        elif event:
            details = []
            if 'oldvalue' in attr or 'newvalue' in attr:
                details.append('%s -> %s' % (self._shownValue(attr.get('oldvalue')),
                                             self._shownValue(attr.get('newvalue'))))
            for name in (attr.get('changed_attributes') or '').split(','):
                if name:
                    details.append('%s: %s -> %s' % (name, self._shownValue(attr.get('old_%s' % name)),
                                                     self._shownValue(attr.get('new_%s' % name))))
            caption = '%s: %s %s' % (caption, event, '; '.join(details))
        attr['caption'] = caption

    def _shownValue(self, value):
        if value is None:
            return ''
        if isinstance(value, Bag):
            return 'Bag(%s)' % ','.join(value.keys())
        return '%r' % (value,)
