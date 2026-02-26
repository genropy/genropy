"""Tests for RE_SQL_PARAMS regex — verifies that :: cast syntax is not
matched as a named parameter.

Ref #585
"""

import re
import pytest


# The two regex variants used across adapters, with lookbehind + lookahead fix.
RE_VARIANT_S = re.compile(r"(?<!:):(?!:)(\S\w*)(\W|$)")   # gnrpostgres3, gnrpostgres, gnrfourd
RE_VARIANT_W = re.compile(r"(?<!:):(?!:)(\w*)(\W|$)")      # gnrpostgres8000, gnrmysql, gnrmssql, gnrdb2_400


@pytest.fixture(params=[RE_VARIANT_S, RE_VARIANT_W], ids=['S_variant', 'W_variant'])
def regex(request):
    return request.param


class TestNamedParams:
    """Named parameters (:name) must still be matched."""

    def test_simple_param(self, regex):
        assert regex.search(":name")

    def test_param_in_where(self, regex):
        sql = "WHERE id = :id AND status = :status"
        matches = [m.group(1) for m in regex.finditer(sql)]
        assert matches == ['id', 'status']

    def test_param_at_end(self, regex):
        sql = "WHERE id = :id"
        matches = [m.group(1) for m in regex.finditer(sql)]
        assert matches == ['id']

    def test_param_with_parens(self, regex):
        sql = "WHERE id IN (:ids)"
        matches = [m.group(1) for m in regex.finditer(sql)]
        assert matches == ['ids']


class TestDoubleCastIgnored:
    """PostgreSQL :: cast syntax must NOT be matched."""

    def test_double_colon_vector(self, regex):
        sql = "embedding::vector"
        matches = [m.group(1) for m in regex.finditer(sql)]
        assert matches == []

    def test_double_colon_text(self, regex):
        sql = "col::text"
        matches = [m.group(1) for m in regex.finditer(sql)]
        assert matches == []

    def test_double_colon_integer(self, regex):
        sql = "val::integer"
        matches = [m.group(1) for m in regex.finditer(sql)]
        assert matches == []

    def test_double_colon_jsonb(self, regex):
        sql = "data::jsonb"
        matches = [m.group(1) for m in regex.finditer(sql)]
        assert matches == []

    def test_cast_in_expression(self, regex):
        sql = "(1 - (embedding <=> CAST(:target AS vector)))"
        matches = [m.group(1) for m in regex.finditer(sql)]
        assert matches == ['target']

    def test_cast_shorthand_with_param(self, regex):
        sql = "WHERE x::text = :val"
        matches = [m.group(1) for m in regex.finditer(sql)]
        assert matches == ['val']


class TestMixed:
    """Queries mixing :: casts and :params."""

    def test_vector_similarity_query(self, regex):
        sql = "SELECT (1 - (emb <=> :target::vector)) AS sim WHERE emb IS NOT NULL"
        matches = [m.group(1) for m in regex.finditer(sql)]
        assert matches == ['target']

    def test_multiple_casts_and_params(self, regex):
        sql = "WHERE col::text ILIKE :pattern AND num::integer > :threshold"
        matches = [m.group(1) for m in regex.finditer(sql)]
        assert matches == ['pattern', 'threshold']
