"""Matrix of "SQL macro x position in the query" as the compiler behaves.

Regression net for issue #617, which moved macro expansion from the
hardcoded ``FINDER.sub(...)`` calls scattered in
``gnr/sql/gnrsqldata/compiler.py`` to the context aware registry
``db._macro_registry``.  Every assertion records the behaviour of the
compiler, including the positions where a macro is left in the SQL as a
literal.

Expansion contexts, each one a ``macro_expander.replace_context(...)`` call
in the compiler:

================  ==================================  =========================
context           where the compiler calls it         macros expanded there
================  ==================================  =========================
``formula_pre``   sql_formula, before updateFieldDict  TSRANK, TSHEADLINE,
                                                       VECRANK
``formula_post``  sql_formula, after updateFieldDict   IN_RANGE
``join_cnd``      ``cnd`` / ``join_on`` of a join      IN_RANGE
``where``         where clause                         IN_RANGE, PERIOD,
                                                       TSQUERY, VECQUERY
``columns``       select list, after updateFieldDict   BAG, BAGCOLS
``columns_final`` select list, last step               TSRANK, TSHEADLINE,
                                                       VECRANK
``order_by``      order by clause                      TSRANK, VECRANK
================  ==================================  =========================

A macro registered with ``contexts=None`` is expanded in every one of them.

``#ENV``, ``#PREF`` and ``#THIS`` are not registry macros: closures of
``getFieldAlias`` expand them in ``sql_formula`` (and ``#THIS`` also in the
where of a ``select_`` subquery).

``group_by``, ``having`` and the extra condition set by
``SqlQuery.setJoinCondition`` have no expansion call at all.

On PostgreSQL only, ``gnr/sql/adapters/gnrpostgres.py`` L194-L197 runs a
second, independent pass (``TsVectorCompiler``) over the whole assembled
statement.  It expands the two-argument forms ``#TSQUERY(fld, :par)``,
``#TSRANK(fld, :par)`` and ``#TSHEADLINE(fld, :par)`` wherever they survived,
which is why some PostgreSQL cells differ from SQLite.
"""

import re

import pytest

from core.common import BaseGnrTest


def setup_module(module):
    BaseGnrTest.setup_class()


def teardown_module(module):
    BaseGnrTest.teardown_class()


# Relation carrying a model level ``cnd``, patched to host a macro.
CND_RELATION_PATH = 'invc.invoice.@discount_tier_id'

# Environment used by every compilation, so values are deterministic.
TEST_ENV = dict(storename='', workdate='2024-06-15', user='admin', locale='en')


@pytest.fixture(scope='module', params=['sqlite', 'pg'])
def db_any(request):
    """The same matrix compiled on both implementations."""
    return request.getfixturevalue('db_%s' % request.param)


@pytest.fixture()
def patch_cnd(db_any):
    """Replace the model ``cnd`` of a relation, restore it afterwards."""
    node = db_any.model.relations.getNode(CND_RELATION_PATH)
    original = node.attr['cnd']

    def _patch(cnd):
        node.attr['cnd'] = cnd

    yield _patch
    node.attr['cnd'] = original


# -- query builders, one per position --------------------------------------

def compile_product(db, position, macro, **params):
    """Compile a query on invc.product with *macro* placed in *position*.

    Returns the SqlQuery; read ``sqltext`` / ``sqlparams`` from it.
    """
    kwargs = dict(params)
    if position == 'where':
        kwargs.update(columns='$code', where=macro)
    elif position == 'columns':
        kwargs.update(columns='$code, %s AS probe_col' % macro)
    elif position == 'order_by':
        kwargs.update(columns='$code', order_by=macro)
    elif position == 'group_by':
        kwargs.update(columns='$code', group_by=macro)
    elif position == 'having':
        kwargs.update(columns='$code, count(*) AS n', group_by='$code', having=macro)
    elif position == 'sql_formula':
        kwargs.update(columns='$code,$probe',
                      probe=dict(field='price_label', sql_formula=macro))
    else:
        raise ValueError('unknown position %s' % position)
    return db.table('invc.product').query(**kwargs)


def compile_rel_cnd(db, patch, macro, **params):
    """Compile a query whose join is driven by a model ``cnd`` holding *macro*."""
    patch(macro)
    return db.table('invc.invoice').query(
        columns='$inv_number,@discount_tier_id.description', **params)


def compile_join_condition(db, macro, **params):
    """Compile a query with *macro* inside a setJoinCondition condition."""
    query = db.table('invc.invoice').query(
        columns='$inv_number,@customer_id.account_name')
    query.setJoinCondition(relation='@customer_id', condition=macro, **params)
    return query


PRODUCT_POSITIONS = ('where', 'columns', 'order_by', 'group_by', 'having', 'sql_formula')


def literal(name):
    """The macro call as it appears before expansion."""
    return '#%s' % name


# -- IN_RANGE ---------------------------------------------------------------

IN_RANGE_MACRO = '#IN_RANGE($unit_price,:lo,:hi)'


class TestInRange:
    """#IN_RANGE: contexts where, formula_post and join_cnd."""

    @pytest.mark.parametrize('position,expanded', [
        ('where', True),
        ('columns', False),        # today: not expanded in this position
        ('order_by', False),       # today: not expanded in this position
        ('group_by', False),       # today: not expanded in this position
        ('having', False),         # today: not expanded in this position
        ('sql_formula', True),
    ])
    def test_positions(self, db_any, position, expanded):
        with db_any.tempEnv(**TEST_ENV):
            sqltext = compile_product(db_any, position, IN_RANGE_MACRO,
                                      lo=1, hi=500).sqltext
        assert (literal('IN_RANGE') not in sqltext) is expanded

    def test_where_sql_fragment(self, db_any):
        with db_any.tempEnv(**TEST_ENV):
            query = compile_product(db_any, 'where', IN_RANGE_MACRO, lo=1, hi=500)
            sqltext = query.sqltext
            params = dict(query.sqlparams)
        assert ':lo IS NULL AND :hi IS NOT NULL' in sqltext
        assert 'unit_price' in sqltext
        # No parameter is added or renamed: the bounds stay as written.
        assert params['lo'] == 1
        assert params['hi'] == 500

    def test_sql_formula_sql_fragment(self, db_any):
        with db_any.tempEnv(**TEST_ENV):
            query = compile_product(db_any, 'sql_formula', IN_RANGE_MACRO, lo=1, hi=500)
            sqltext = query.sqltext
            params = dict(query.sqlparams)
        assert ':lo IS NOT NULL AND :hi IS NOT NULL' in sqltext
        assert params['lo'] == 1
        assert params['hi'] == 500

    def test_sql_formula_var_renames_parameters(self, db_any):
        """``var_`` attributes rename ``:par`` into ``:env_<id>_<col>_<par>``.

        getFieldAlias writes the value into ``db.currentEnv`` under
        ``<id>_<col>_<par>`` (no ``env_`` prefix) and rewrites the SQL token
        with the prefix.
        """
        with db_any.tempEnv(**TEST_ENV):
            query = db_any.table('invc.product').query(
                columns='$code,$probe',
                probe=dict(field='price_label', sql_formula=IN_RANGE_MACRO,
                           var_lo=1, var_hi=500))
            sqltext = query.sqltext
            env_keys = [k for k in db_any.currentEnv if k.endswith('_probe_lo')]
            env_values = [db_any.currentEnv[k] for k in env_keys]
        assert re.search(r':env_\d+_probe_lo\b', sqltext)
        assert re.search(r':env_\d+_probe_hi\b', sqltext)
        assert ':lo' not in sqltext
        assert env_values == [1]

    def test_relation_cnd_expanded(self, db_any, patch_cnd):
        with db_any.tempEnv(**TEST_ENV):
            sqltext = compile_rel_cnd(
                db_any, patch_cnd,
                '#IN_RANGE(@discount_tier_id.min_amount,:lo,:hi)',
                lo=1, hi=500).sqltext
        assert literal('IN_RANGE') not in sqltext
        assert 'min_amount' in sqltext
        assert ':lo IS NULL AND :hi IS NOT NULL' in sqltext

    def test_join_condition_not_expanded(self, db_any):
        # today: not expanded in this position (setJoinCondition has no
        # expansion call, unlike the model cnd, which is the join_cnd context)
        with db_any.tempEnv(**TEST_ENV):
            sqltext = compile_join_condition(
                db_any, '#IN_RANGE($total,:lo,:hi)', lo=1, hi=500).sqltext
        assert literal('IN_RANGE') in sqltext


# -- PERIOD -----------------------------------------------------------------

PERIOD_MACRO_PRODUCT = '#PERIOD($unit_price,period)'
PERIOD_MACRO_INVOICE = '#PERIOD($date,period)'


class TestPeriod:
    """#PERIOD: context where only."""

    @pytest.mark.parametrize('position,expanded', [
        ('where', True),
        ('columns', False),        # today: not expanded in this position
        ('order_by', False),       # today: not expanded in this position
        ('group_by', False),       # today: not expanded in this position
        ('having', False),         # today: not expanded in this position
        ('sql_formula', False),    # today: not expanded in this position
    ])
    def test_positions(self, db_any, position, expanded):
        with db_any.tempEnv(**TEST_ENV):
            sqltext = compile_product(db_any, position, PERIOD_MACRO_PRODUCT,
                                      period='2024').sqltext
        assert (literal('PERIOD') not in sqltext) is expanded

    def test_where_adds_from_and_to_parameters(self, db_any):
        with db_any.tempEnv(**TEST_ENV):
            query = db_any.table('invc.invoice').query(
                columns='$inv_number', where=PERIOD_MACRO_INVOICE, period='2024')
            sqltext = query.sqltext
            params = dict(query.sqlparams)
        assert literal('PERIOD') not in sqltext
        assert 'BETWEEN :period_from AND :period_to' in sqltext
        # gnrsqlmacros.expand_period adds these two keys to sqlparams.
        assert params['period_from'].isoformat() == '2024-01-01'
        assert params['period_to'].isoformat() == '2024-12-31'

    def test_where_single_day_adds_only_from(self, db_any):
        with db_any.tempEnv(**TEST_ENV):
            query = db_any.table('invc.invoice').query(
                columns='$inv_number', where=PERIOD_MACRO_INVOICE,
                period='2024-06-15')
            sqltext = query.sqltext
            params = dict(query.sqlparams)
        assert '= :period_from' in sqltext
        assert 'period_to' not in params

    def test_relation_cnd_not_expanded(self, db_any, patch_cnd):
        # today: not expanded in this position -- join_cnd runs IN_RANGE only
        with db_any.tempEnv(**TEST_ENV):
            sqltext = compile_rel_cnd(db_any, patch_cnd, PERIOD_MACRO_INVOICE,
                                      period='2024').sqltext
        assert literal('PERIOD') in sqltext

    def test_join_condition_not_expanded(self, db_any):
        # today: not expanded in this position
        with db_any.tempEnv(**TEST_ENV):
            sqltext = compile_join_condition(
                db_any, PERIOD_MACRO_INVOICE, period='2024').sqltext
        assert literal('PERIOD') in sqltext


# -- ENV --------------------------------------------------------------------

ENV_MACRO = '#ENV(workdate)'


class TestEnv:
    """#ENV: sql_formula only, through a closure of getFieldAlias."""

    @pytest.mark.parametrize('position,expanded', [
        ('where', False),          # today: not expanded in this position
        ('columns', False),        # today: not expanded in this position
        ('order_by', False),       # today: not expanded in this position
        ('group_by', False),       # today: not expanded in this position
        ('having', False),         # today: not expanded in this position
        ('sql_formula', True),
    ])
    def test_positions(self, db_any, position, expanded):
        with db_any.tempEnv(**TEST_ENV):
            sqltext = compile_product(db_any, position, ENV_MACRO).sqltext
        assert (literal('ENV') not in sqltext) is expanded

    def test_sql_formula_inlines_a_quoted_literal(self, db_any):
        with db_any.tempEnv(**TEST_ENV):
            query = compile_product(db_any, 'sql_formula', ENV_MACRO)
            sqltext = query.sqltext
            params = dict(query.sqlparams)
        assert "'2024-06-15'" in sqltext
        # The value is inlined in the SQL: no parameter is added.
        assert 'workdate' not in params

    def test_relation_cnd_not_expanded(self, db_any, patch_cnd):
        # today: not expanded in this position
        with db_any.tempEnv(**TEST_ENV):
            sqltext = compile_rel_cnd(
                db_any, patch_cnd,
                '@discount_tier_id.description=#ENV(workdate)').sqltext
        assert literal('ENV') in sqltext

    def test_join_condition_not_expanded(self, db_any):
        # today: not expanded in this position
        with db_any.tempEnv(**TEST_ENV):
            sqltext = compile_join_condition(
                db_any, '$inv_number=#ENV(workdate)').sqltext
        assert literal('ENV') in sqltext


# -- PREF -------------------------------------------------------------------

PREF_MACRO = '#PREF(some.path,fallback)'


class TestPref:
    """#PREF: sql_formula only, through a closure of getFieldAlias."""

    @pytest.mark.parametrize('position,expanded', [
        ('where', False),          # today: not expanded in this position
        ('columns', False),        # today: not expanded in this position
        ('order_by', False),       # today: not expanded in this position
        ('group_by', False),       # today: not expanded in this position
        ('having', False),         # today: not expanded in this position
        ('sql_formula', True),
    ])
    def test_positions(self, db_any, position, expanded):
        with db_any.tempEnv(**TEST_ENV):
            sqltext = compile_product(db_any, position, PREF_MACRO).sqltext
        assert (literal('PREF') not in sqltext) is expanded

    def test_sql_formula_inlines_the_default(self, db_any):
        """No preference is stored, so the default is inlined unquoted."""
        with db_any.tempEnv(**TEST_ENV):
            query = compile_product(db_any, 'sql_formula', PREF_MACRO)
            sqltext = query.sqltext
            params = dict(query.sqlparams)
        assert '( fallback )' in sqltext
        assert 'some.path' not in params

    def test_relation_cnd_not_expanded(self, db_any, patch_cnd):
        # today: not expanded in this position
        with db_any.tempEnv(**TEST_ENV):
            sqltext = compile_rel_cnd(
                db_any, patch_cnd,
                '@discount_tier_id.description=#PREF(some.path,fallback)').sqltext
        assert literal('PREF') in sqltext

    def test_join_condition_not_expanded(self, db_any):
        # today: not expanded in this position
        with db_any.tempEnv(**TEST_ENV):
            sqltext = compile_join_condition(
                db_any, '$inv_number=#PREF(some.path,fallback)').sqltext
        assert literal('PREF') in sqltext


# -- THIS -------------------------------------------------------------------

THIS_MACRO = '#THIS.unit_price'


class TestThis:
    """#THIS: sql_formula and the where of a ``select_`` subquery."""

    @pytest.mark.parametrize('position,expanded', [
        ('where', False),          # today: not expanded in this position
        ('columns', False),        # today: not expanded in this position
        ('order_by', False),       # today: not expanded in this position
        ('group_by', False),       # today: not expanded in this position
        ('having', False),         # today: not expanded in this position
        ('sql_formula', True),
    ])
    def test_positions(self, db_any, position, expanded):
        with db_any.tempEnv(**TEST_ENV):
            sqltext = compile_product(db_any, position, THIS_MACRO).sqltext
        assert (literal('THIS') not in sqltext) is expanded

    def test_sql_formula_resolves_to_the_current_alias(self, db_any):
        with db_any.tempEnv(**TEST_ENV):
            sqltext = compile_product(db_any, 'sql_formula', THIS_MACRO).sqltext
        assert re.search(r'\(\s*"t0"\."unit_price"\s*\) AS "probe"', sqltext)

    def test_subselect_where_expanded(self, db_any):
        """invc.invoice.row_count is a model column whose subquery uses #THIS.id."""
        with db_any.tempEnv(**TEST_ENV):
            sqltext = db_any.table('invc.invoice').query(
                columns='$inv_number,$row_count').sqltext
        assert literal('THIS') not in sqltext
        assert 'COUNT(*)' in sqltext

    def test_relation_cnd_not_expanded(self, db_any, patch_cnd):
        # today: not expanded in this position
        with db_any.tempEnv(**TEST_ENV):
            sqltext = compile_rel_cnd(
                db_any, patch_cnd,
                '@discount_tier_id.min_amount=#THIS.total').sqltext
        assert literal('THIS') in sqltext

    def test_join_condition_not_expanded(self, db_any):
        # today: not expanded in this position
        with db_any.tempEnv(**TEST_ENV):
            sqltext = compile_join_condition(db_any, '$total=#THIS.total').sqltext
        assert literal('THIS') in sqltext


# -- BAG / BAGCOLS ----------------------------------------------------------

BAG_MACRO = '#BAG($description)'
BAGCOLS_MACRO = '#BAGCOLS($description)'


class TestBag:
    """#BAG and #BAGCOLS: context columns only."""

    @pytest.mark.parametrize('macro_name,macro', [
        ('BAG', BAG_MACRO),
        ('BAGCOLS', BAGCOLS_MACRO),
    ])
    @pytest.mark.parametrize('position,expanded', [
        ('where', False),          # today: not expanded in this position
        ('columns', True),
        ('order_by', False),       # today: not expanded in this position
        ('group_by', False),       # today: not expanded in this position
        ('having', False),         # today: not expanded in this position
        ('sql_formula', False),    # today: not expanded in this position
    ])
    def test_positions(self, db_any, macro_name, macro, position, expanded):
        with db_any.tempEnv(**TEST_ENV):
            sqltext = compile_product(db_any, position, macro).sqltext
        assert (literal(macro_name) not in sqltext) is expanded

    def test_columns_bag_registers_the_column(self, db_any):
        with db_any.tempEnv(**TEST_ENV):
            query = compile_product(db_any, 'columns', BAG_MACRO)
            sqltext = query.sqltext
            evaluated = list(query.compiled.evaluateBagColumns)
            params = dict(query.sqlparams)
        assert '"description" AS probe_col' in sqltext
        assert ('probe_col', False) in evaluated
        assert 'probe_col' not in params

    def test_columns_bagcols_registers_the_column(self, db_any):
        with db_any.tempEnv(**TEST_ENV):
            query = compile_product(db_any, 'columns', BAGCOLS_MACRO)
            sqltext = query.sqltext
            evaluated = list(query.compiled.evaluateBagColumns)
        assert '"description" AS probe_col' in sqltext
        assert ('probe_col', True) in evaluated

    def test_relation_cnd_not_expanded(self, db_any, patch_cnd):
        # today: not expanded in this position
        with db_any.tempEnv(**TEST_ENV):
            sqltext = compile_rel_cnd(
                db_any, patch_cnd,
                '#BAG(@discount_tier_id.description) IS NOT NULL').sqltext
        assert literal('BAG') in sqltext

    def test_join_condition_not_expanded(self, db_any):
        # today: not expanded in this position
        with db_any.tempEnv(**TEST_ENV):
            sqltext = compile_join_condition(
                db_any, '#BAG($inv_number) IS NOT NULL').sqltext
        assert literal('BAG') in sqltext


# -- PROBE_UPPER (macro added through db.addMacro) --------------------------

PROBE_MACRO = '#PROBE_UPPER($description)'
PROBE_FINDER = re.compile(r'#PROBE_UPPER\(([^)]+)\)')


def _expand_probe(match, compiler):
    return 'UPPER(%s)' % match.group(1)


@pytest.fixture()
def probe_macro(db_any):
    """Add ``#PROBE_UPPER`` to the registry, drop it after the test.

    Yields the registration function, so a test can register the macro
    again with a different ``contexts``.
    """
    def _register(contexts=None):
        db_any.addMacro('PROBE_UPPER', PROBE_FINDER, _expand_probe,
                        contexts=contexts, replace=True)

    _register()
    yield _register
    del db_any._macro_registry['PROBE_UPPER']


class TestPackageMacro:
    """A macro added with ``db.addMacro`` is expanded by the compiler.

    ``SqlQueryCompiler`` builds its MacroExpander from
    ``db._macro_registry``, so a macro registered with ``contexts=None``
    is expanded in every context.
    """

    def test_macro_is_registered(self, db_any, probe_macro):
        assert 'PROBE_UPPER' in db_any._macro_registry

    @pytest.mark.parametrize('position,expanded', [
        ('where', True),
        ('columns', True),
        ('order_by', True),
        ('group_by', False),       # no expansion call in this position
        ('having', False),         # no expansion call in this position
        ('sql_formula', True),
    ])
    def test_positions(self, db_any, probe_macro, position, expanded):
        with db_any.tempEnv(**TEST_ENV):
            sqltext = compile_product(db_any, position, PROBE_MACRO).sqltext
        assert (literal('PROBE_UPPER') not in sqltext) is expanded

    def test_relation_cnd_expanded(self, db_any, patch_cnd, probe_macro):
        with db_any.tempEnv(**TEST_ENV):
            sqltext = compile_rel_cnd(
                db_any, patch_cnd,
                '#PROBE_UPPER(@discount_tier_id.description)=:x', x='A').sqltext
        assert literal('PROBE_UPPER') not in sqltext
        assert 'UPPER(' in sqltext

    def test_join_condition_not_expanded(self, db_any, probe_macro):
        # no expansion call in this position
        with db_any.tempEnv(**TEST_ENV):
            sqltext = compile_join_condition(
                db_any, '#PROBE_UPPER($inv_number)=:x', x='A').sqltext
        assert literal('PROBE_UPPER') in sqltext

    def test_contexts_restrict_the_positions(self, db_any, probe_macro):
        """With ``contexts='where'`` the macro expands in where only."""
        probe_macro('where')
        with db_any.tempEnv(**TEST_ENV):
            where_sql = compile_product(db_any, 'where', PROBE_MACRO).sqltext
            columns_sql = compile_product(db_any, 'columns', PROBE_MACRO).sqltext
        assert literal('PROBE_UPPER') not in where_sql
        assert literal('PROBE_UPPER') in columns_sql


# -- PostgreSQL only macros on SQLite --------------------------------------

PG_ONLY_MACROS = [
    ('TSQUERY', '#TSQUERY($description,:q)'),
    ('TSRANK', '#TSRANK'),
    ('TSHEADLINE', '#TSHEADLINE($description)'),
    ('VECQUERY', '#VECQUERY($description,:v)'),
    ('VECRANK', '#VECRANK'),
]


class TestPgOnlyMacrosOnSqlite:
    """The SQLite adapter registers no macros, so all five stay literal."""

    @pytest.mark.parametrize('macro_name,macro', PG_ONLY_MACROS)
    @pytest.mark.parametrize('position', PRODUCT_POSITIONS)
    def test_never_expanded(self, db_sqlite, macro_name, macro, position):
        # today: not expanded in any position on sqlite
        with db_sqlite.tempEnv(**TEST_ENV):
            sqltext = compile_product(db_sqlite, position, macro,
                                      q='hello', v='[1,2]').sqltext
        assert literal(macro_name) in sqltext


# -- TSQUERY / TSRANK / TSHEADLINE on PostgreSQL ---------------------------

TSQUERY_MACRO = '#TSQUERY($description,:q)'


class TestTsqueryPg:
    """#TSQUERY: context where plus the TsVectorCompiler pass on the full SQL."""

    @pytest.mark.parametrize('position,expanded', [
        ('where', True),
        ('columns', True),         # by TsVectorCompiler, not by columns_final
        ('order_by', True),        # by TsVectorCompiler, not by order_by
        ('group_by', True),        # expanded by TsVectorCompiler only
        ('having', True),          # expanded by TsVectorCompiler only
        ('sql_formula', True),     # expanded by TsVectorCompiler only
    ])
    def test_positions(self, db_pg, position, expanded):
        with db_pg.tempEnv(**TEST_ENV):
            sqltext = compile_product(db_pg, position, TSQUERY_MACRO, q='hello').sqltext
        assert (literal('TSQUERY') not in sqltext) is expanded

    def test_where_uses_the_adapter_expander(self, db_pg):
        """The MacroExpander form casts the language to regconfig."""
        with db_pg.tempEnv(**TEST_ENV):
            query = compile_product(db_pg, 'where', TSQUERY_MACRO, q='hello')
            sqltext = query.sqltext
            params = dict(query.sqlparams)
        assert "websearch_to_tsquery(CAST('simple' AS regconfig),:q)" in sqltext
        # expand_tsquery stores the channel dict that #TSRANK later reads.
        assert params['tsquery_current'] == {
            'querystring': ':q', 'language': "'simple'", 'tsv': '$description'}

    def test_columns_uses_the_tsvectorcompiler_form(self, db_pg):
        """Outside the where clause a different expander produces the SQL."""
        with db_pg.tempEnv(**TEST_ENV):
            query = compile_product(db_pg, 'columns', TSQUERY_MACRO, q='hello')
            sqltext = query.sqltext
            params = dict(query.sqlparams)
        assert "websearch_to_tsquery('simple', :q)" in sqltext
        assert 'CAST' not in sqltext
        # No channel dict: TsVectorCompiler does not touch sqlparams.
        assert 'tsquery_current' not in params


class TestTsrankPg:
    """#TSRANK: contexts columns_final, order_by and formula_pre."""

    @pytest.mark.parametrize('position,expanded', [
        ('columns', True),
        ('order_by', True),
        ('sql_formula', True),
        ('where', False),          # today: not expanded in this position
        ('group_by', False),       # today: not expanded in this position
        ('having', False),         # today: not expanded in this position
    ])
    def test_positions(self, db_pg, position, expanded):
        macro = '%s AND %s' % (TSQUERY_MACRO, '#TSRANK') if position == 'where' else '#TSRANK'
        with db_pg.tempEnv(**TEST_ENV):
            query = db_pg.table('invc.product').query(
                **_with_tsquery(position, macro))
            sqltext = query.sqltext
        assert (literal('TSRANK') not in sqltext) is expanded

    def test_columns_emits_an_untranslated_column_token(self, db_pg):
        """columns_final runs after updateFieldDict, so ``$description`` survives."""
        with db_pg.tempEnv(**TEST_ENV):
            query = db_pg.table('invc.product').query(
                columns='$code, #TSRANK AS rank', where=TSQUERY_MACRO, q='hello')
            sqltext = query.sqltext
            params = dict(query.sqlparams)
        assert 'ts_rank(ARRAY[0.1, 0.2, 0.4, 1.0],$description,' in sqltext
        assert '"t0"."description", websearch_to_tsquery' not in sqltext
        assert params['tsquery_current']['tsv'] == '$description'

    def test_order_by_emits_an_untranslated_column_token(self, db_pg):
        with db_pg.tempEnv(**TEST_ENV):
            sqltext = db_pg.table('invc.product').query(
                columns='$code', order_by='#TSRANK', where=TSQUERY_MACRO,
                q='hello').sqltext
        assert 'ORDER BY ts_rank(ARRAY[0.1, 0.2, 0.4, 1.0],$description,' in sqltext

    def test_sql_formula_translates_the_column(self, db_pg):
        """formula_pre runs before updateFieldDict, so the alias is correct here."""
        with db_pg.tempEnv(**TEST_ENV):
            sqltext = db_pg.table('invc.product').query(
                columns='$code,$probe', where=TSQUERY_MACRO, q='hello',
                probe=dict(field='price_label', sql_formula='#TSRANK')).sqltext
        assert '"t0"."description", websearch_to_tsquery' in sqltext


def _with_tsquery(position, macro):
    """Query kwargs placing *macro* in *position*, with a #TSQUERY in where."""
    kwargs = dict(q='hello')
    if position == 'where':
        kwargs.update(columns='$code', where=macro)
        return kwargs
    kwargs['where'] = TSQUERY_MACRO
    if position == 'columns':
        kwargs.update(columns='$code, %s AS probe_col' % macro)
    elif position == 'order_by':
        kwargs.update(columns='$code', order_by=macro)
    elif position == 'group_by':
        kwargs.update(columns='$code', group_by=macro)
    elif position == 'having':
        kwargs.update(columns='$code, count(*) AS n', group_by='$code', having=macro)
    elif position == 'sql_formula':
        kwargs.update(columns='$code,$probe',
                      probe=dict(field='price_label', sql_formula=macro))
    else:
        raise ValueError('unknown position %s' % position)
    return kwargs


class TestTsheadlinePg:
    """#TSHEADLINE: one-argument form only in columns_final and formula_pre."""

    @pytest.mark.parametrize('position,expanded', [
        ('sql_formula', True),
        ('columns', False),        # today: not expanded in this position
        ('where', False),          # today: not expanded in this position
        ('order_by', False),       # today: not expanded in this position
        ('group_by', False),       # today: not expanded in this position
        ('having', False),         # today: not expanded in this position
    ])
    def test_positions_one_argument_form(self, db_pg, position, expanded):
        macro = '#TSHEADLINE($description)'
        with db_pg.tempEnv(**TEST_ENV):
            sqltext = db_pg.table('invc.product').query(
                **_with_tsquery(position, macro)).sqltext
        assert (literal('TSHEADLINE') not in sqltext) is expanded

    def test_columns_one_argument_form_survives(self, db_pg):
        """columns_final runs after updateFieldDict rewrote ``$description``.

        The adapter regex requires a ``$`` or ``@`` prefixed field, so the
        already translated ``"t0"."description"`` no longer matches.
        """
        with db_pg.tempEnv(**TEST_ENV):
            sqltext = db_pg.table('invc.product').query(
                columns='$code, #TSHEADLINE($description) AS hl',
                where=TSQUERY_MACRO, q='hello').sqltext
        assert '#TSHEADLINE("t0"."description")' in sqltext

    @pytest.mark.parametrize('position', PRODUCT_POSITIONS)
    def test_two_argument_form_always_expanded(self, db_pg, position):
        """The TsVectorCompiler pass catches the two-argument form everywhere."""
        macro = '#TSHEADLINE($description,:q)'
        with db_pg.tempEnv(**TEST_ENV):
            sqltext = compile_product(db_pg, position, macro, q='hello').sqltext
        assert literal('TSHEADLINE') not in sqltext
        assert 'ts_headline(' in sqltext


# -- VECQUERY / VECRANK on PostgreSQL --------------------------------------

VECQUERY_MACRO = '#VECQUERY($description,:v)'


class TestVecqueryPg:
    """#VECQUERY: context where only; no TsVectorCompiler fallback exists."""

    @pytest.mark.parametrize('position,expanded', [
        ('where', True),
        ('columns', False),        # today: not expanded in this position
        ('order_by', False),       # today: not expanded in this position
        ('group_by', False),       # today: not expanded in this position
        ('having', False),         # today: not expanded in this position
        ('sql_formula', False),    # today: not expanded in this position
    ])
    def test_positions(self, db_pg, position, expanded):
        with db_pg.tempEnv(**TEST_ENV):
            sqltext = compile_product(db_pg, position, VECQUERY_MACRO,
                                      v='[1,2]').sqltext
        assert (literal('VECQUERY') not in sqltext) is expanded

    def test_where_stores_the_channel_parameters(self, db_pg):
        with db_pg.tempEnv(**TEST_ENV):
            query = compile_product(db_pg, 'where', VECQUERY_MACRO, v='[1,2]')
            sqltext = query.sqltext
            params = dict(query.sqlparams)
        assert '"t0"."description" IS NOT NULL' in sqltext
        assert params['vecquery_current'] == {'veccol': '$description', 'target': ':v'}


class TestVecrankPg:
    """#VECRANK: contexts columns_final, order_by and formula_pre."""

    @pytest.mark.parametrize('position,expanded', [
        ('columns', True),
        ('order_by', True),
        ('sql_formula', True),
        ('group_by', False),       # today: not expanded in this position
        ('having', False),         # today: not expanded in this position
    ])
    def test_positions(self, db_pg, position, expanded):
        kwargs = _with_vecquery(position, '#VECRANK')
        with db_pg.tempEnv(**TEST_ENV):
            sqltext = db_pg.table('invc.product').query(**kwargs).sqltext
        assert (literal('VECRANK') not in sqltext) is expanded

    def test_where_without_vecquery_raises(self, db_pg):
        """expand_vecrank reads the channel dict written by #VECQUERY."""
        with db_pg.tempEnv(**TEST_ENV):
            with pytest.raises(KeyError):
                db_pg.table('invc.product').query(
                    columns='$code, #VECRANK AS sim').sqltext

    def test_columns_emits_an_untranslated_column_token(self, db_pg):
        with db_pg.tempEnv(**TEST_ENV):
            sqltext = db_pg.table('invc.product').query(
                columns='$code, #VECRANK AS sim', where=VECQUERY_MACRO,
                v='[1,2]').sqltext
        assert '(1 - ($description <=> CAST(:v AS vector))) AS sim' in sqltext

    def test_sql_formula_translates_the_column(self, db_pg):
        with db_pg.tempEnv(**TEST_ENV):
            sqltext = db_pg.table('invc.product').query(
                columns='$code,$probe', where=VECQUERY_MACRO, v='[1,2]',
                probe=dict(field='price_label', sql_formula='#VECRANK')).sqltext
        assert '(1 - ("t0"."description" <=> CAST(:v AS vector)))' in sqltext


def _with_vecquery(position, macro):
    """Query kwargs placing *macro* in *position*, with a #VECQUERY in where."""
    kwargs = dict(v='[1,2]', where=VECQUERY_MACRO)
    if position == 'columns':
        kwargs.update(columns='$code, %s AS probe_col' % macro)
    elif position == 'order_by':
        kwargs.update(columns='$code', order_by=macro)
    elif position == 'group_by':
        kwargs.update(columns='$code', group_by=macro)
    elif position == 'having':
        kwargs.update(columns='$code, count(*) AS n', group_by='$code', having=macro)
    elif position == 'sql_formula':
        kwargs.update(columns='$code,$probe',
                      probe=dict(field='price_label', sql_formula=macro))
    else:
        raise ValueError('unknown position %s' % position)
    return kwargs
