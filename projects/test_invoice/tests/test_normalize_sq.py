"""Unit tests for normalize_subquery_dict (pure function, no DB needed)."""

import pytest
from gnr.sql.gnrsqldata.subquery_utils import normalize_subquery_dict


class TestNormalizeSubqueryDict:
    """Test the legacy -> canonical subquery dict normalization."""

    def test_new_syntax_noop(self):
        """If join_to is already present, dict is left untouched."""
        sq = dict(
            table='invc.invoice',
            columns='COUNT(*)',
            join_to='$customer_id',
            join_from='id',
        )
        original = dict(sq)
        normalize_subquery_dict(sq)
        assert sq == original

    def test_new_syntax_with_condition_noop(self):
        """New syntax with join_condition is left untouched."""
        sq = dict(
            table='invc.invoice',
            columns='COUNT(*)',
            join_to='$customer_id',
            join_from='id',
            join_condition='$active=true',
        )
        original = dict(sq)
        normalize_subquery_dict(sq)
        assert sq == original

    def test_legacy_simple(self):
        """Basic legacy where with #THIS is converted."""
        sq = dict(
            table='invc.invoice',
            columns='COUNT(*)',
            where='$customer_id=#THIS.id',
        )
        normalize_subquery_dict(sq)
        assert sq['join_to'] == '$customer_id'
        assert sq['join_from'] == 'id'
        assert sq['join_condition'] is None
        assert 'where' not in sq

    def test_legacy_with_and_condition(self):
        """Legacy where with AND residual splits into join_condition."""
        sq = dict(
            table='invc.invoice',
            columns='COUNT(*)',
            where='$customer_id=#THIS.id AND $active=true',
        )
        normalize_subquery_dict(sq)
        assert sq['join_to'] == '$customer_id'
        assert sq['join_from'] == 'id'
        assert sq['join_condition'] == '$active=true'
        assert 'where' not in sq

    def test_legacy_with_complex_condition(self):
        """Legacy where with multiple AND conditions after #THIS."""
        sq = dict(
            table='invc.invoice',
            columns='SUM($total)',
            where="$customer_id=#THIS.id AND $active=true AND $year=2024",
        )
        normalize_subquery_dict(sq)
        assert sq['join_to'] == '$customer_id'
        assert sq['join_from'] == 'id'
        assert sq['join_condition'] == '$active=true AND $year=2024'
        assert 'where' not in sq

    def test_legacy_with_at_relation(self):
        """Legacy where with @relation.field syntax for join_to."""
        sq = dict(
            table='invc.invoice_row',
            columns='COUNT(*)',
            where='@invoice_id.customer_id=#THIS.id',
        )
        normalize_subquery_dict(sq)
        assert sq['join_to'] == '@invoice_id.customer_id'
        assert sq['join_from'] == 'id'
        assert sq['join_condition'] is None
        assert 'where' not in sq

    def test_legacy_spaces_around_equals(self):
        """Spaces around = are handled."""
        sq = dict(
            table='invc.invoice',
            columns='COUNT(*)',
            where='$customer_id = #THIS.id',
        )
        normalize_subquery_dict(sq)
        assert sq['join_to'] == '$customer_id'
        assert sq['join_from'] == 'id'

    def test_legacy_lowercase_and(self):
        """AND keyword is case-insensitive."""
        sq = dict(
            table='invc.invoice',
            columns='COUNT(*)',
            where='$customer_id=#THIS.id and $active=true',
        )
        normalize_subquery_dict(sq)
        assert sq['join_to'] == '$customer_id'
        assert sq['join_condition'] == '$active=true'

    def test_uncorrelated_subquery_untouched(self):
        """A where without #THIS is left untouched."""
        sq = dict(
            table='invc.invoice',
            columns='COUNT(*)',
            where='$active=true',
        )
        original = dict(sq)
        normalize_subquery_dict(sq)
        assert sq == original

    def test_no_where_untouched(self):
        """Dict without where is left untouched."""
        sq = dict(
            table='invc.invoice',
            columns='COUNT(*)',
        )
        original = dict(sq)
        normalize_subquery_dict(sq)
        assert sq == original

    def test_empty_where_untouched(self):
        """Empty where string is left untouched."""
        sq = dict(
            table='invc.invoice',
            columns='COUNT(*)',
            where='',
        )
        original = dict(sq)
        normalize_subquery_dict(sq)
        assert sq == original

    def test_other_keys_preserved(self):
        """Keys not involved in normalization are preserved."""
        sq = dict(
            table='invc.invoice',
            columns='COUNT(*)',
            where='$customer_id=#THIS.id',
            group_by='$year',
            order_by='$date DESC',
            limit=1,
        )
        normalize_subquery_dict(sq)
        assert sq['table'] == 'invc.invoice'
        assert sq['columns'] == 'COUNT(*)'
        assert sq['group_by'] == '$year'
        assert sq['order_by'] == '$date DESC'
        assert sq['limit'] == 1

    def test_exists_flag_preserved(self):
        """The exists flag is preserved through normalization."""
        sq = dict(
            table='invc.invoice',
            columns='*',
            where='$customer_id=#THIS.id',
            exists=True,
        )
        normalize_subquery_dict(sq)
        assert sq['exists'] is True
        assert sq['join_to'] == '$customer_id'

    def test_join_from_different_field(self):
        """join_from captures a non-pkey field correctly."""
        sq = dict(
            table='invc.invoice',
            columns='COUNT(*)',
            where='$tax_code=#THIS.fiscal_code',
        )
        normalize_subquery_dict(sq)
        assert sq['join_to'] == '$tax_code'
        assert sq['join_from'] == 'fiscal_code'
