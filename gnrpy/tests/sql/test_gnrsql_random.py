# -*- coding: utf-8 -*-
import random
from datetime import date, time, datetime
from unittest.mock import MagicMock, patch, call

import pytest

from gnr.sql.gnrsql_random import RandomRecordGenerator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_column(dtype='T', size=None, sysfield=False, related_table=None):
    col = MagicMock()
    col.attributes = {'dtype': dtype}
    if size:
        col.attributes['size'] = size
    if sysfield:
        col.attributes['_sysfield'] = True
    col.relatedTable.return_value = related_table
    return col


def _make_tblobj(columns_spec, random_values=None):
    """Build a mock tblobj.

    columns_spec: dict of {col_name: column_mock}
    random_values: dict returned by tblobj.randomValues()
    """
    tblobj = MagicMock()
    tblobj.columns = columns_spec
    tblobj.db = MagicMock()
    if random_values is not None:
        tblobj.randomValues.return_value = random_values
    else:
        del tblobj.randomValues  # hasattr will return False
    return tblobj


# ---------------------------------------------------------------------------
# _buildFieldsConfig
# ---------------------------------------------------------------------------

class TestBuildFieldsConfig:

    def test_sysfield_skipped(self):
        cols = {'id': _make_column(dtype='L', sysfield=True),
                'name': _make_column(dtype='T')}
        tblobj = _make_tblobj(cols)
        gen = RandomRecordGenerator(tblobj)
        fields = gen._buildFieldsConfig()
        assert 'id' not in fields
        assert 'name' in fields

    def test_dtype_X_skipped(self):
        cols = {'blob_col': _make_column(dtype='X'),
                'name': _make_column(dtype='T')}
        tblobj = _make_tblobj(cols)
        gen = RandomRecordGenerator(tblobj)
        fields = gen._buildFieldsConfig()
        assert 'blob_col' not in fields

    def test_randomValues_merged(self):
        cols = {'price': _make_column(dtype='N')}
        rv = {'price': {'min_value': 10, 'max_value': 100}}
        tblobj = _make_tblobj(cols, random_values=rv)
        gen = RandomRecordGenerator(tblobj)
        fields = gen._buildFieldsConfig()
        assert fields['price']['min_value'] == 10
        assert fields['price']['max_value'] == 100
        assert fields['price']['dtype'] == 'N'

    def test_config_overrides_randomValues(self):
        cols = {'price': _make_column(dtype='N')}
        rv = {'price': {'min_value': 10, 'max_value': 100}}
        tblobj = _make_tblobj(cols, random_values=rv)
        gen = RandomRecordGenerator(tblobj, config={'price': {'min_value': 50}})
        fields = gen._buildFieldsConfig()
        assert fields['price']['min_value'] == 50
        assert fields['price']['max_value'] == 100

    def test_config_false_excludes_field(self):
        cols = {'price': _make_column(dtype='N')}
        rv = {'price': False}
        tblobj = _make_tblobj(cols, random_values=rv)
        gen = RandomRecordGenerator(tblobj)
        fields = gen._buildFieldsConfig()
        assert 'price' not in fields

    def test_size_from_column(self):
        cols = {'code': _make_column(dtype='T', size='5:20')}
        tblobj = _make_tblobj(cols)
        gen = RandomRecordGenerator(tblobj)
        fields = gen._buildFieldsConfig()
        assert fields['code']['size'] == '5:20'


# ---------------------------------------------------------------------------
# Conversion utilities
# ---------------------------------------------------------------------------

class TestConversions:

    def setup_method(self):
        tblobj = _make_tblobj({})
        self.gen = RandomRecordGenerator(tblobj)

    def test_time_roundtrip(self):
        t = time(14, 30)
        n = self.gen._convertToNumber(t, 'H')
        assert n == 14 * 60 + 30
        assert self.gen._convertFromNumber(n, 'H') == t

    def test_date_roundtrip(self):
        d = date(2024, 6, 15)
        n = self.gen._convertToNumber(d, 'D')
        assert self.gen._convertFromNumber(n, 'D') == d

    def test_numeric(self):
        assert self.gen._convertToNumber('3.14', 'N') == 3.14


# ---------------------------------------------------------------------------
# _randomValue
# ---------------------------------------------------------------------------

class TestRandomValue:

    def setup_method(self):
        tblobj = _make_tblobj({})
        self.gen = RandomRecordGenerator(tblobj)

    def test_integer_in_range(self):
        for _ in range(50):
            v = self.gen._randomValue(1, 10, 'I')
            assert 1 <= v <= 10
            assert isinstance(v, int)

    def test_float_in_range(self):
        for _ in range(50):
            v = self.gen._randomValue(1.0, 10.0, 'N')
            assert 1.0 <= v <= 10.0

    def test_min_greater_than_max_handled(self):
        v = self.gen._randomValue(10, 1, 'I')
        assert 1 <= v <= 10


# ---------------------------------------------------------------------------
# _randomTextValue
# ---------------------------------------------------------------------------

class TestRandomTextValue:

    def setup_method(self):
        tblobj = _make_tblobj({})
        self.gen = RandomRecordGenerator(tblobj)

    def test_default_produces_capitalized_words(self):
        random.seed(42)
        text = self.gen._randomTextValue()
        assert text[0].isupper()
        words = text.split()
        assert 2 <= len(words) <= 5

    def test_fixed_n_words(self):
        random.seed(42)
        text = self.gen._randomTextValue(n_words=3, w_length='5:5')
        words = text.split()
        assert len(words) == 3
        for w in words:
            assert len(w) == 5


# ---------------------------------------------------------------------------
# _setRecordField — scalar types
# ---------------------------------------------------------------------------

class TestSetRecordField:

    def setup_method(self):
        cols = {
            'flag': _make_column(dtype='B'),
            'name': _make_column(dtype='T', size='50'),
            'amount': _make_column(dtype='N'),
            'ref': _make_column(dtype='T'),
        }
        tblobj = _make_tblobj(cols)
        self.gen = RandomRecordGenerator(tblobj)

    def test_boolean_field(self):
        random.seed(42)
        r = {}
        self.gen._setRecordField(r, 'flag', {'dtype': 'B', 'true_value': 100}, 0)
        assert r['flag'] is True

    def test_text_default_value(self):
        r = {}
        pars = {'dtype': 'T', 'default_value': '#P-#N', 'size': '50'}
        self.gen._setRecordField(r, 'name', pars, 0, batch_prefix='TST')
        assert r['name'] == 'TST-1'

    def test_text_truncated_to_size(self):
        r = {}
        pars = {'dtype': 'T', 'default_value': 'ABCDEFGHIJ', 'size': '5'}
        self.gen._setRecordField(r, 'name', pars, 0)
        assert len(r['name']) == 5

    def test_equal_to(self):
        r = {'ref': 'hello'}
        pars = {'equal_to': 'ref'}
        self.gen._setRecordField(r, 'name', pars, 0)
        assert r['name'] == 'hello'

    def test_values_list(self):
        r = {}
        pars = {'values': ['a', 'b', 'c']}
        self.gen._setRecordField(r, 'name', pars, 1)
        assert r['name'] == 'b'

    def test_numeric_range(self):
        r = {}
        cols = {'amount': _make_column(dtype='N')}
        tblobj = _make_tblobj(cols)
        gen = RandomRecordGenerator(tblobj)
        random.seed(42)
        pars = {'dtype': 'N', 'min_value': 10, 'max_value': 20}
        gen._setRecordField(r, 'amount', pars, 0)
        assert 10 <= r['amount'] <= 20


# ---------------------------------------------------------------------------
# _checkCondition
# ---------------------------------------------------------------------------

class TestCheckCondition:

    def setup_method(self):
        tblobj = _make_tblobj({})
        self.gen = RandomRecordGenerator(tblobj)

    def test_positive_condition(self):
        assert self.gen._checkCondition({'active': True}, 'active') is True
        assert self.gen._checkCondition({'active': False}, 'active') is False

    def test_negated_condition(self):
        assert self.gen._checkCondition({'active': True}, '!active') is False
        assert self.gen._checkCondition({'active': False}, '!active') is True


# ---------------------------------------------------------------------------
# generate — integration with mocks
# ---------------------------------------------------------------------------

class TestGenerate:

    def test_inserts_correct_count(self):
        cols = {'name': _make_column(dtype='T')}
        tblobj = _make_tblobj(cols, random_values={
            'name': {'default_value': 'test_#N'}
        })
        gen = RandomRecordGenerator(tblobj)
        gen.generate(5, seed=42)
        assert tblobj.insert.call_count == 5
        tblobj.db.commit.assert_called_once()

    def test_seed_reproducibility(self):
        cols = {'val': _make_column(dtype='I')}
        rv = {'val': {'min_value': 1, 'max_value': 1000}}

        def run_with_seed(seed):
            tblobj = _make_tblobj(cols, random_values=dict(rv))
            gen = RandomRecordGenerator(tblobj)
            gen.generate(10, seed=seed)
            return [c.args[0]['val'] for c in tblobj.insert.call_args_list]

        run1 = run_with_seed(123)
        run2 = run_with_seed(123)
        assert run1 == run2

    def test_null_perc_skips_some(self):
        cols = {'name': _make_column(dtype='T')}
        tblobj = _make_tblobj(cols, random_values={
            'name': {'default_value': 'X', 'null_perc': 99}
        })
        gen = RandomRecordGenerator(tblobj)
        gen.generate(100, seed=42)
        records = [c.args[0] for c in tblobj.insert.call_args_list]
        names_set = [r.get('name') for r in records]
        none_count = names_set.count(None)
        assert none_count > 0  # with 99% null, most should be None

    def test_condition_if(self):
        cols = {
            'is_active': _make_column(dtype='B'),
            'detail': _make_column(dtype='T'),
        }
        tblobj = _make_tblobj(cols, random_values={
            'is_active': {'true_value': 0},  # always False
            'detail': {'default_value': 'hello', '_if': 'is_active'},
        })
        gen = RandomRecordGenerator(tblobj)
        gen.generate(5, seed=42)
        records = [c.args[0] for c in tblobj.insert.call_args_list]
        for r in records:
            assert 'detail' not in r  # condition never met


# ---------------------------------------------------------------------------
# GnrSqlDb.createRandomRecords integration
# ---------------------------------------------------------------------------

class TestDbCreateRandomRecords:

    def test_extract_kwargs_wiring(self):
        from gnr.sql.gnrsql import GnrSqlDb
        db = GnrSqlDb()
        assert hasattr(db, 'createRandomRecords')

    def test_config_kwargs_parsing(self):
        """config_price_min_value=5 should become config={'price': {'min_value': 5}}"""
        from gnr.sql.gnrsql import GnrSqlDb
        db = GnrSqlDb()
        with patch('gnr.sql.gnrsql_random.RandomRecordGenerator') as MockGen:
            mock_instance = MockGen.return_value
            mock_instance.generate = MagicMock()
            with patch.object(db, 'table') as mock_table:
                mock_table.return_value = MagicMock()
                db.createRandomRecords('pkg.mytable', how_many=5,
                                       config_price_min_value=5,
                                       config_price_max_value=100)
                config_passed = MockGen.call_args[1]['config']
                assert config_passed['price']['min_value'] == 5
                assert config_passed['price']['max_value'] == 100

    def test_config_dict_passed_through(self):
        from gnr.sql.gnrsql import GnrSqlDb
        db = GnrSqlDb()
        with patch('gnr.sql.gnrsql_random.RandomRecordGenerator') as MockGen:
            mock_instance = MockGen.return_value
            mock_instance.generate = MagicMock()
            with patch.object(db, 'table') as mock_table:
                mock_table.return_value = MagicMock()
                cfg = {'amount': {'min_value': 10}}
                db.createRandomRecords('pkg.mytable', how_many=3, config=cfg)
                config_passed = MockGen.call_args[1]['config']
                assert config_passed['amount']['min_value'] == 10


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------

class TestCLI:

    def test_module_has_description(self):
        from gnr.db.cli import gnrrandom_records
        assert hasattr(gnrrandom_records, 'description')
        assert gnrrandom_records.description

    def test_module_has_main(self):
        from gnr.db.cli import gnrrandom_records
        assert callable(gnrrandom_records.main)

    def test_cli_invocation(self):
        """Test that CLI correctly wires args to db.createRandomRecords"""
        import sys
        from gnr.db.cli import gnrrandom_records

        test_argv = ['gnr db random_records',
                     'fatt.fattura', '-n', '50', '--seed', '42']

        mock_app = MagicMock()
        mock_db = mock_app.db

        with patch.object(sys, 'argv', test_argv), \
             patch('gnr.db.cli.gnrrandom_records.get_app',
                   return_value=(mock_app, None)):
            gnrrandom_records.main()

        mock_db.createRandomRecords.assert_called_once_with(
            'fatt.fattura',
            how_many=50,
            seed=42,
            batch_prefix='RND'
        )

    def test_cli_with_store(self):
        """Test that storename triggers use_store"""
        import sys
        from gnr.db.cli import gnrrandom_records

        test_argv = ['gnr db random_records', 'pkg.tbl']

        mock_app = MagicMock()

        with patch.object(sys, 'argv', test_argv), \
             patch('gnr.db.cli.gnrrandom_records.get_app',
                   return_value=(mock_app, 'mystore')):
            gnrrandom_records.main()

        mock_app.db.use_store.assert_called_once_with('mystore')
