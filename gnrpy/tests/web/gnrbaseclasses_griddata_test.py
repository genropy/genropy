"""Regression tests for selection ordering in TableScriptToHtml.gridData()."""

from core.common import BaseGnrAppTest
from gnr.core.gnrbag import Bag
from gnr.web.gnrbaseclasses import TableScriptToHtml


PAYMENT_TYPES = [
    ('C1', 'Cash'),
    ('C2', 'Bank transfer'),
    ('C3', 'Credit card'),
    ('C4', 'Check'),
]


class _FakeExportParent:
    export_mode = True


class _GridDataResource(TableScriptToHtml):
    grid_sqlcolumns = 'code,description'
    grid_subtotal_order_by = None

    def gridQueryParameters(self):
        return dict(table='invc.payment_type')


def _make_resource(db, selection_pkeys, use_current_selection=False,
                   export_mode=False):
    obj = _GridDataResource.__new__(_GridDataResource)
    obj.db = db
    obj.row_table = None
    obj.parent = _FakeExportParent() if export_mode else None
    obj._parameters = Bag()
    if use_current_selection:
        obj._parameters['use_current_selection'] = True
    obj.record = Bag(dict(selectionPkeys=selection_pkeys))
    return obj


def _codes(data):
    if isinstance(data, Bag):
        return [node.attr.get('code') for node in data]
    return [row['code'] for row in data]


class TestGridDataSelectionOrder(BaseGnrAppTest):
    app_name = 'test_invoice'

    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.app.db.model.check(applyChanges=True)
        table = cls.app.db.table('invc.payment_type')
        for code, description in PAYMENT_TYPES:
            table.insert(dict(code=code, description=description))
        cls.app.db.commit()

    def test_partial_selection_print(self):
        resource = _make_resource(self.app.db, selection_pkeys=['C1', 'C3'])

        codes = _codes(resource.gridData())

        assert codes[:2] == ['C1', 'C3']
        assert len(codes) == 4
        assert set(codes[2:]) == {'C2', 'C4'}

    def test_current_selection_export(self):
        resource = _make_resource(
            self.app.db,
            selection_pkeys=['C3', 'C1'],
            use_current_selection=True,
            export_mode=True,
        )

        assert _codes(resource.gridData()) == ['C3', 'C1']

    def test_contained_resource_query_preserves_selection_order(self):
        selection_pkeys = ['C4', 'C2', 'C3', 'C1']
        resource = _make_resource(
            self.app.db,
            selection_pkeys=selection_pkeys,
            export_mode=True,
        )

        assert _codes(resource.gridData()) == selection_pkeys
