"""Full-output reference for every macro/position cell that expands today.

Companion of ``test_macro_contexts.py``.  That module asserts only *whether*
a macro is expanded; this one pins the whole result of the compilation, so
the refactor of ``gnr/sql/gnrsqldata/compiler.py`` planned for issue #617 can
be checked as behaviour preserving down to the character.

For every **E** / **E\\*** cell of ``temp/macro_context_matrix.md`` the test
stores three things in
``tests/sql/data/macro_reference/<backend>/<macro>__<position>.json``:

``sqltext``
    the whole compiled statement;
``sqlparams``
    the bind parameters, JSON encoded (``Decimal`` as string, dates as
    ISO 8601, anything else through ``str``);
``env_diff``
    the keys of ``db.currentEnv`` added or changed by the compilation,
    measured inside the same ``db.tempEnv(**TEST_ENV)`` block.  ``sql_comment``
    and ``sql_details`` are left out: they carry the module, function and line
    number of the caller, so they describe this test file rather than the
    macro, and they survive from one test to the next (``tempEnv`` restores
    only the keys it set), which would make a cell depend on the cells run
    before it.

First run writes the missing files and passes.  Later runs compare and fail
with a unified diff.  ``GNR_MACRO_REFERENCE_UPDATE=1`` rewrites them all.

Normalisation
-------------
Two values change at every process start and are rewritten before comparison:

- ``compiler.py`` L429 builds the ``var_`` parameter prefix with
  ``str(id(fldalias))``, a memory address.  The regex ``\\d+_probe_`` becomes
  ``<id>_probe_``, turning ``:env_4412887312_probe_lo`` into
  ``:env_<id>_probe_lo`` in the SQL text and in the ``env_diff`` keys.
- some ``env_diff`` values are objects without a ``__repr__``
  (``DbColAliasListObj``, ``TriggerStack``).  The regex
  ``object at 0x[0-9a-f]+>`` becomes ``object at 0x<addr>>``.

Nothing else needed normalising: join aliases and subquery alias prefixes are
counters restarted at every compilation.
"""

import datetime
import decimal
import difflib
import json
import os
import re

import pytest

from core.common import BaseGnrTest

from .test_macro_contexts import (BAG_MACRO, BAGCOLS_MACRO, ENV_MACRO,
                                  IN_RANGE_MACRO, PERIOD_MACRO_PRODUCT,
                                  PREF_MACRO, PRODUCT_POSITIONS, TEST_ENV,
                                  THIS_MACRO, TSQUERY_MACRO, VECQUERY_MACRO,
                                  _with_tsquery, _with_vecquery,
                                  compile_product, compile_rel_cnd)
from .test_macro_contexts import db_any, patch_cnd  # noqa: F401


def setup_module(module):
    BaseGnrTest.setup_class()


def teardown_module(module):
    BaseGnrTest.teardown_class()


DATA_DIR = os.path.join(os.path.dirname(__file__), 'data', 'macro_reference')

VAR_PREFIX = re.compile(r'\d+_probe_')
OBJECT_ADDRESS = re.compile(r'object at 0x[0-9a-f]+>')

# Written by the call site bookkeeping, not by macro expansion.
ENV_CALLER_KEYS = ('sql_comment', 'sql_details')

TSHEADLINE_MACRO = '#TSHEADLINE($description)'
TSHEADLINE_2ARG_MACRO = '#TSHEADLINE($description,:q)'


# -- reference handling -----------------------------------------------------

def _normalise(text):
    """Drop the two values that change at every process start."""
    return OBJECT_ADDRESS.sub('object at 0x<addr>>', VAR_PREFIX.sub('<id>_probe_', text))


def _jsonable(value):
    """Deterministic JSON representation of a bind parameter or env value."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, decimal.Decimal):
        return str(value)
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, dict):
        return {_normalise(str(k)): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in value]
    return _normalise(str(value))


def _pretty(payload):
    return json.dumps(payload, indent=2, sort_keys=True)


def _compile_reference(db, build, patch):
    """Compile through *build* and return the three recorded values."""
    with db.tempEnv(**TEST_ENV):
        before = dict(db.currentEnv)
        query = build(db, patch)
        sqltext = query.sqltext
        sqlparams = dict(query.sqlparams)
        after = dict(db.currentEnv)
    env_diff = {k: v for k, v in after.items()
                if k not in ENV_CALLER_KEYS and (k not in before or before[k] != v)}
    return {'sqltext': _normalise(sqltext),
            'sqlparams': _jsonable(sqlparams),
            'env_diff': _jsonable(env_diff)}


def _check_reference(db, macro, position, build, patch=None):
    actual = _compile_reference(db, build, patch)
    path = os.path.join(DATA_DIR, db.implementation,
                        '%s__%s.json' % (macro, position))
    if os.environ.get('GNR_MACRO_REFERENCE_UPDATE') == '1' or not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as reference_file:
            json.dump(actual, reference_file, indent=2, sort_keys=True)
            reference_file.write('\n')
        return
    with open(path) as reference_file:
        expected = json.load(reference_file)
    if expected == actual:
        return
    diff = difflib.unified_diff(_pretty(expected).splitlines(),
                                _pretty(actual).splitlines(),
                                fromfile='reference: %s' % path,
                                tofile='compiled now', lineterm='')
    pytest.fail('%s %s differs from its reference\n%s'
                % (macro, position, '\n'.join(diff)))


# -- cells expanded on both backends ---------------------------------------

def _formula_var(db, patch):
    return db.table('invc.product').query(
        columns='$code,$probe',
        probe=dict(field='price_label', sql_formula=IN_RANGE_MACRO,
                   var_lo=1, var_hi=500))


COMMON_CASES = [
    ('IN_RANGE', 'where',
     lambda db, patch: compile_product(db, 'where', IN_RANGE_MACRO, lo=1, hi=500)),
    ('IN_RANGE', 'sql_formula',
     lambda db, patch: compile_product(db, 'sql_formula', IN_RANGE_MACRO, lo=1, hi=500)),
    ('IN_RANGE', 'sql_formula_var', _formula_var),
    ('IN_RANGE', 'model_cnd',
     lambda db, patch: compile_rel_cnd(
         db, patch, '#IN_RANGE(@discount_tier_id.min_amount,:lo,:hi)', lo=1, hi=500)),
    ('PERIOD', 'where',
     lambda db, patch: compile_product(db, 'where', PERIOD_MACRO_PRODUCT, period='2024')),
    ('ENV', 'sql_formula',
     lambda db, patch: compile_product(db, 'sql_formula', ENV_MACRO)),
    ('PREF', 'sql_formula',
     lambda db, patch: compile_product(db, 'sql_formula', PREF_MACRO)),
    ('THIS', 'sql_formula',
     lambda db, patch: compile_product(db, 'sql_formula', THIS_MACRO)),
    ('BAG', 'columns',
     lambda db, patch: compile_product(db, 'columns', BAG_MACRO)),
    ('BAGCOLS', 'columns',
     lambda db, patch: compile_product(db, 'columns', BAGCOLS_MACRO)),
]


# -- cells expanded on PostgreSQL only -------------------------------------

def _pg_channel_case(macro_name, position, macro, with_channel):
    """A case whose query needs a #TSQUERY / #VECQUERY in the where clause."""
    return (macro_name, position,
            lambda db, patch: db.table('invc.product').query(
                **with_channel(position, macro)))


PG_CASES = [
    (macro_name, position,
     lambda db, patch, _p=position, _m=macro: compile_product(db, _p, _m, q='hello'))
    for macro_name, macro in (('TSQUERY', TSQUERY_MACRO),
                              ('TSHEADLINE_2ARG', TSHEADLINE_2ARG_MACRO))
    for position in PRODUCT_POSITIONS
] + [
    _pg_channel_case('TSRANK', 'columns', '#TSRANK', _with_tsquery),
    _pg_channel_case('TSRANK', 'order_by', '#TSRANK', _with_tsquery),
    _pg_channel_case('TSRANK', 'sql_formula', '#TSRANK', _with_tsquery),
    _pg_channel_case('TSHEADLINE', 'sql_formula', TSHEADLINE_MACRO, _with_tsquery),
    ('VECQUERY', 'where',
     lambda db, patch: compile_product(db, 'where', VECQUERY_MACRO, v='[1,2]')),
    _pg_channel_case('VECRANK', 'columns', '#VECRANK', _with_vecquery),
    _pg_channel_case('VECRANK', 'order_by', '#VECRANK', _with_vecquery),
    _pg_channel_case('VECRANK', 'sql_formula', '#VECRANK', _with_vecquery),
]


def _ids(cases):
    return ['%s__%s' % (macro, position) for macro, position, _ in cases]


@pytest.mark.parametrize('macro,position,build', COMMON_CASES, ids=_ids(COMMON_CASES))
def test_common_reference(db_any, patch_cnd, macro, position, build):  # noqa: F811
    _check_reference(db_any, macro, position, build, patch_cnd)


@pytest.mark.parametrize('macro,position,build', PG_CASES, ids=_ids(PG_CASES))
def test_pg_reference(db_pg, macro, position, build):
    _check_reference(db_pg, macro, position, build)
