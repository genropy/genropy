"""Tests for VECQUERY/VECRANK macros in the PostgreSQL MacroExpander.

Verifies regex matching, parameter storage in sqlparams, and SQL expansion
for vector similarity search macros. Also includes regression tests to
ensure existing TSQUERY/TSRANK/TSHEADLINE macros are not broken.

Ref #583
"""

import pytest
from gnr.sql.adapters._gnrbasepostgresadapter import MacroExpander


class FakeQueryCompiler:
    """Minimal stand-in for SqlQueryCompiler — only needs sqlparams."""

    def __init__(self):
        self.sqlparams = {}


@pytest.fixture
def expander():
    return MacroExpander(FakeQueryCompiler())


# --- VECQUERY ---

class TestVecquery:

    def test_basic_expansion(self, expander):
        sql = "#VECQUERY($embedding, :target_vec)"
        result = expander.replace(sql, 'VECQUERY')
        assert result == "$embedding IS NOT NULL"

    def test_stores_params(self, expander):
        expander.replace("#VECQUERY($embedding, :target_vec)", 'VECQUERY')
        params = expander.querycompiler.sqlparams
        assert 'vecquery_current' in params
        assert params['vecquery_current']['veccol'] == '$embedding'
        assert params['vecquery_current']['target'] == ':target_vec'

    def test_channel_code(self, expander):
        sql = "#VECQUERY_secondary($other_emb, :other_vec)"
        result = expander.replace(sql, 'VECQUERY')
        assert result == "$other_emb IS NOT NULL"
        assert 'vecquery_secondary' in expander.querycompiler.sqlparams

    def test_dotted_column(self, expander):
        sql = "#VECQUERY($rel.@table.embedding, :vec)"
        result = expander.replace(sql, 'VECQUERY')
        assert result == "$rel.@table.embedding IS NOT NULL"

    def test_dollar_target(self, expander):
        sql = "#VECQUERY($embedding, $other_embedding)"
        result = expander.replace(sql, 'VECQUERY')
        assert result == "$embedding IS NOT NULL"
        assert expander.querycompiler.sqlparams['vecquery_current']['target'] == '$other_embedding'


# --- VECRANK ---

class TestVecrank:

    def test_basic_expansion(self, expander):
        expander.replace("#VECQUERY($embedding, :target_vec)", 'VECQUERY')
        result = expander.replace("#VECRANK", 'VECRANK')
        assert result == "(1 - ($embedding <=> CAST(:target_vec AS vector)))"

    def test_channel_code(self, expander):
        expander.replace("#VECQUERY_alt($emb, :v)", 'VECQUERY')
        result = expander.replace("#VECRANK_alt", 'VECRANK')
        assert result == "(1 - ($emb <=> CAST(:v AS vector)))"

    def test_missing_vecquery_raises(self, expander):
        with pytest.raises(KeyError):
            expander.replace("#VECRANK", 'VECRANK')


# --- Combined expansion (simulates compiler pipeline) ---

class TestCombined:

    def test_where_columns_orderby(self, expander):
        where = "#VECQUERY($embedding, :target_vec) AND $kind = 'function'"
        columns = "$name, $kind, #VECRANK AS similarity"
        order_by = "#VECRANK DESC"

        where_out = expander.replace(where, 'TSQUERY,VECQUERY')
        cols_out = expander.replace(columns, 'TSRANK,TSHEADLINE,VECRANK')
        order_out = expander.replace(order_by, 'TSRANK,VECRANK')

        assert where_out == "$embedding IS NOT NULL AND $kind = 'function'"
        assert cols_out == "$name, $kind, (1 - ($embedding <=> CAST(:target_vec AS vector))) AS similarity"
        assert order_out == "(1 - ($embedding <=> CAST(:target_vec AS vector))) DESC"

    def test_two_channels(self, expander):
        where = "#VECQUERY($emb_a, :vec_a) AND #VECQUERY_b($emb_b, :vec_b)"
        columns = "#VECRANK AS sim_a, #VECRANK_b AS sim_b"

        expander.replace(where, 'VECQUERY')
        cols_out = expander.replace(columns, 'VECRANK')

        assert "(1 - ($emb_a <=> CAST(:vec_a AS vector))) AS sim_a" in cols_out
        assert "(1 - ($emb_b <=> CAST(:vec_b AS vector))) AS sim_b" in cols_out


# --- Regression: TSQUERY/TSRANK still work ---

class TestTsRegressions:

    def test_tsquery_still_works(self, expander):
        sql = "#TSQUERY($tsv, :search_text)"
        result = expander.replace(sql, 'TSQUERY')
        assert "websearch_to_tsquery" in result
        assert "@@ websearch_to_tsquery" in result

    def test_tsrank_still_works(self, expander):
        expander.replace("#TSQUERY($tsv, :q)", 'TSQUERY')
        result = expander.replace("#TSRANK", 'TSRANK')
        assert "ts_rank" in result

    def test_tsheadline_still_works(self, expander):
        expander.replace("#TSQUERY($tsv, :q)", 'TSQUERY')
        result = expander.replace("#TSHEADLINE($content)", 'TSHEADLINE')
        assert "ts_headline" in result
