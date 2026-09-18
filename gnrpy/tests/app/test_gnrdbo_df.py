"""Tests for the dynamic-fields helpers in gnr.app.gnrdbo (TableBase.df_*).

Uses the shared test_invoice fixture from this directory's conftest:
``invc.product.details`` is a subfields column pointing to
``invc.product_type``, which carries ``df_fields`` (sysFields df=True).
"""

from gnr.core.gnrbag import Bag

from core.common import BaseGnrTest


def setup_module(module):
    BaseGnrTest.setup_class()


def teardown_module(module):
    BaseGnrTest.teardown_class()


def _df_field(code, data_type, querable=True):
    return Bag(dict(code=code, description='Field %s' % code,
                    data_type=data_type, querable=querable))


class TestDfGetQuerableFields:

    def _setup_df_fields(self, db, data_types):
        """Store a df_fields Bag on the first product_type record."""
        tbl = db.table('invc.product_type')
        pkey = tbl.query(order_by='$id', limit=1).fetch()[0]['id']
        df_fields = Bag()
        for i, data_type in enumerate(data_types):
            df_fields['f_%02i' % i] = _df_field('fld_%s' % data_type.lower(),
                                                data_type)
        with tbl.recordToUpdate(pkey) as rec:
            rec['df_fields'] = df_fields
        db.commit()
        return pkey

    def _querable(self, db, pkey):
        tbl = db.table('invc.product')
        rows = tbl.df_getQuerableFields('details', caption_field='description',
                                        where='$id=:pk', pk=pkey)
        return {r['name'].split('_', 1)[1]: r for r in rows}

    def test_base_dtypes_previously_missing(self, db_sqlite):
        # issue #22 (helpers.py twin): I, DH, DHZ, HZ, F, Z raised KeyError
        pkey = self._setup_df_fields(db_sqlite,
                                     ['I', 'DH', 'DHZ', 'HZ', 'F', 'Z'])
        byfield = self._querable(db_sqlite, pkey)
        assert 'AS integer' in byfield['fld_i']['sql_formula']
        assert 'AS timestamp without time zone' in byfield['fld_dh']['sql_formula']
        assert 'AS timestamp with time zone' in byfield['fld_dhz']['sql_formula']
        assert 'AS time with time zone' in byfield['fld_hz']['sql_formula']
        assert 'AS real' in byfield['fld_f']['sql_formula']
        assert 'AS text' in byfield['fld_z']['sql_formula']

    def test_custom_dtype_falls_back_to_text(self, db_sqlite):
        # custom dtypes (e.g. 'money') must not raise KeyError
        pkey = self._setup_df_fields(db_sqlite, ['money', 'N'])
        byfield = self._querable(db_sqlite, pkey)
        assert 'AS text' in byfield['fld_money']['sql_formula']
        assert 'AS numeric' in byfield['fld_n']['sql_formula']

    def test_not_querable_fields_are_skipped(self, db_sqlite):
        db = db_sqlite
        tbl = db.table('invc.product_type')
        pkey = tbl.query(order_by='$id', limit=1).fetch()[0]['id']
        df_fields = Bag()
        df_fields['f_00'] = _df_field('fld_yes', 'T')
        df_fields['f_01'] = _df_field('fld_no', 'T', querable=False)
        with tbl.recordToUpdate(pkey) as rec:
            rec['df_fields'] = df_fields
        db.commit()
        byfield = self._querable(db, pkey)
        assert 'fld_yes' in byfield
        assert 'fld_no' not in byfield
