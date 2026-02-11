# -*- coding: utf-8 -*-
import random
import sys
from datetime import date, time
from unittest.mock import MagicMock, patch
import json as json_mod
        
from gnr.sql.gnrsql import GnrSqlDb
from gnr.sql.gnrsql_random import RandomRecordGenerator
from gnr.sql.gnrsql_random import parse_typed_value, load_config_file
from gnr.db.cli import gnrrandom_records

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
        db = GnrSqlDb()
        assert hasattr(db, 'createRandomRecords')

    def test_config_kwargs_parsing(self):
        """config_price_min_value=5 should become config={'price': {'min_value': 5}}"""
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
# load_config_file and parse_typed_value
# ---------------------------------------------------------------------------

class TestConfigFile:

    def test_load_yaml(self, tmp_path):
        f = tmp_path / "cfg.yaml"
        f.write_text("price:\n  min_value: 10\nname:\n  default_value: hello\n")
        result = load_config_file(str(f))
        assert result == {'price': {'min_value': 10}, 'name': {'default_value': 'hello'}}

    def test_load_json(self, tmp_path):
        f = tmp_path / "cfg.json"
        f.write_text(json_mod.dumps({'qty': {'min_value': 1}}))
        result = load_config_file(str(f))
        assert result == {'qty': {'min_value': 1}}

    def test_load_unknown_ext_yaml_content(self, tmp_path):
        f = tmp_path / "cfg.txt"
        f.write_text("amount:\n  max_value: 99\n")
        result = load_config_file(str(f))
        assert result == {'amount': {'max_value': 99}}


class TestParseTypedValue:

    def test_empty_returns_none(self):
        assert parse_typed_value('', 'I', int) is None

    def test_int_conversion(self):
        assert parse_typed_value('42', 'I', int) == 42

    def test_float_conversion(self):
        assert parse_typed_value('3.14', 'N', float) == 3.14

    def test_str_yes_for_text_dtype(self):
        assert parse_typed_value('y', 'T', str) is True
        assert parse_typed_value('yes', 'T', str) is True

    def test_str_no_for_text_dtype(self):
        assert parse_typed_value('n', 'T', str) is None
        assert parse_typed_value('no', 'T', str) is None

    def test_str_passthrough(self):
        assert parse_typed_value('hello #N', 'T', str) == 'hello #N'


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------

class TestCLI:

    def test_module_has_description(self):
        assert hasattr(gnrrandom_records, 'description')
        assert gnrrandom_records.description

    def test_module_has_main(self):
        assert callable(gnrrandom_records.main)

    def test_cli_invocation(self):
        """Test that CLI correctly wires args to db.createRandomRecords"""
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
        test_argv = ['gnr db random_records', 'pkg.tbl']

        mock_app = MagicMock()

        with patch.object(sys, 'argv', test_argv), \
             patch('gnr.db.cli.gnrrandom_records.get_app',
                   return_value=(mock_app, 'mystore')):
            gnrrandom_records.main()

        mock_app.db.use_store.assert_called_once_with('mystore')

    def test_cli_with_config_yaml(self, tmp_path):
        """Test --config loads YAML file and passes config dict"""
        config_file = tmp_path / "fields.yaml"
        config_file.write_text("price:\n  min_value: 10\n  max_value: 100\n")

        test_argv = ['gnr db random_records', 'pkg.tbl',
                     '--config', str(config_file)]

        mock_app = MagicMock()

        with patch.object(sys, 'argv', test_argv), \
             patch('gnr.db.cli.gnrrandom_records.get_app',
                   return_value=(mock_app, None)):
            gnrrandom_records.main()

        call_kwargs = mock_app.db.createRandomRecords.call_args
        assert call_kwargs[1]['config'] == {'price': {'min_value': 10, 'max_value': 100}}

    def test_cli_with_config_json(self, tmp_path):
        """Test --config loads JSON file"""
        config_data = {'name': {'default_value': 'TEST_#N'}}
        config_file = tmp_path / "fields.json"
        config_file.write_text(json_mod.dumps(config_data))

        test_argv = ['gnr db random_records', 'pkg.tbl',
                     '--config', str(config_file)]

        mock_app = MagicMock()

        with patch.object(sys, 'argv', test_argv), \
             patch('gnr.db.cli.gnrrandom_records.get_app',
                   return_value=(mock_app, None)):
            gnrrandom_records.main()

        call_kwargs = mock_app.db.createRandomRecords.call_args
        assert call_kwargs[1]['config'] == {'name': {'default_value': 'TEST_#N'}}

    def test_cli_interactive_confirm(self):
        """Test -I interactive mode with user input"""
        test_argv = ['gnr db random_records', 'pkg.tbl', '-I']

        mock_app = MagicMock()
        mock_tblobj = MagicMock()
        mock_tblobj.fullname = 'pkg.tbl'
        # one numeric column
        col = MagicMock()
        col.attributes = {'dtype': 'N'}
        col.relatedTable.return_value = None
        mock_tblobj.columns = {'amount': col}
        mock_app.db.table.return_value = mock_tblobj

        # simulate user: configure? y, min_value: 5, max_value: 50, proceed? y
        user_inputs = iter(['y', '5', '50', 'y'])

        with patch.object(sys, 'argv', test_argv), \
             patch('gnr.db.cli.gnrrandom_records.get_app',
                   return_value=(mock_app, None)), \
             patch('builtins.input', side_effect=user_inputs):
            gnrrandom_records.main()

        call_kwargs = mock_app.db.createRandomRecords.call_args
        assert call_kwargs[1]['config'] == {'amount': {'min_value': 5.0, 'max_value': 50.0}}

    def test_cli_interactive_abort(self):
        """Test -I interactive mode abort"""
        test_argv = ['gnr db random_records', 'pkg.tbl', '-I']

        mock_app = MagicMock()
        mock_tblobj = MagicMock()
        mock_tblobj.fullname = 'pkg.tbl'
        col = MagicMock()
        col.attributes = {'dtype': 'I'}
        col.relatedTable.return_value = None
        mock_tblobj.columns = {'qty': col}
        mock_app.db.table.return_value = mock_tblobj

        # configure? y, min: 1, max: 10, proceed? n
        user_inputs = iter(['y', '1', '10', 'n'])

        with patch.object(sys, 'argv', test_argv), \
             patch('gnr.db.cli.gnrrandom_records.get_app',
                   return_value=(mock_app, None)), \
             patch('builtins.input', side_effect=user_inputs):
            gnrrandom_records.main()

        mock_app.db.createRandomRecords.assert_not_called()

    def test_cli_interactive_skip_sysfield(self):
        """Test that interactive mode skips system fields"""
        test_argv = ['gnr db random_records', 'pkg.tbl', '-I']

        mock_app = MagicMock()
        mock_tblobj = MagicMock()
        mock_tblobj.fullname = 'pkg.tbl'
        sys_col = MagicMock()
        sys_col.attributes = {'dtype': 'T', '_sysfield': True}
        name_col = MagicMock()
        name_col.attributes = {'dtype': 'T'}
        name_col.relatedTable.return_value = None
        mock_tblobj.columns = {'__ins_ts': sys_col, 'name': name_col}
        mock_app.db.table.return_value = mock_tblobj

        # only name is shown: skip it -> empty config -> no confirm needed
        user_inputs = iter(['n'])

        with patch.object(sys, 'argv', test_argv), \
             patch('gnr.db.cli.gnrrandom_records.get_app',
                   return_value=(mock_app, None)), \
             patch('builtins.input', side_effect=user_inputs):
            gnrrandom_records.main()

        # called without config since all skipped
        call_kwargs = mock_app.db.createRandomRecords.call_args
        assert 'config' not in call_kwargs[1]

    def test_cli_interactive_fk_column(self):
        """Test interactive mode with FK column"""
        test_argv = ['gnr db random_records', 'pkg.tbl', '-I']

        mock_app = MagicMock()
        mock_tblobj = MagicMock()
        mock_tblobj.fullname = 'pkg.tbl'
        fk_col = MagicMock()
        fk_col.attributes = {'dtype': 'T'}
        related = MagicMock()
        related.fullname = 'other.table'
        fk_col.relatedTable.return_value = related
        mock_tblobj.columns = {'other_id': fk_col}
        mock_app.db.table.return_value = mock_tblobj

        # configure? y, WHERE condition: $active=true, proceed? y
        user_inputs = iter(['y', '$active=true', 'y'])

        with patch.object(sys, 'argv', test_argv), \
             patch('gnr.db.cli.gnrrandom_records.get_app',
                   return_value=(mock_app, None)), \
             patch('builtins.input', side_effect=user_inputs):
            gnrrandom_records.main()

        call_kwargs = mock_app.db.createRandomRecords.call_args
        assert call_kwargs[1]['config'] == {'other_id': {'condition': '$active=true'}}
