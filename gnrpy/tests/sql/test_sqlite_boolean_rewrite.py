"""Test for SQLite boolean rewrite in prepareSqlText.

Verifies that IS [NOT] TRUE/FALSE rewrites handle NULL correctly,
matching PostgreSQL's three-valued logic semantics.

Bug #549: the old rewrite turned ``IS NOT TRUE`` into ``!=1``,
but ``NULL != 1`` is ``NULL`` in SQL (not TRUE as in PostgreSQL).
"""

import re
import sqlite3
import pytest


@pytest.fixture(scope='module')
def conn():
    """In-memory SQLite database with a test table."""
    c = sqlite3.connect(':memory:')
    cur = c.cursor()
    cur.execute('CREATE TABLE t (id INTEGER, flag BOOLEAN)')
    cur.execute('INSERT INTO t VALUES (1, NULL)')
    cur.execute('INSERT INTO t VALUES (2, 0)')
    cur.execute('INSERT INTO t VALUES (3, 1)')
    c.commit()
    return c


class TestPostgresSemantics:
    """Expected results based on PostgreSQL three-valued logic.

    PostgreSQL truth table:
        NULL IS TRUE      -> FALSE
        NULL IS NOT TRUE  -> TRUE
        NULL IS FALSE     -> FALSE
        NULL IS NOT FALSE -> TRUE
        0    IS TRUE      -> FALSE
        0    IS NOT TRUE  -> TRUE
        0    IS FALSE     -> TRUE
        0    IS NOT FALSE -> FALSE
        1    IS TRUE      -> TRUE
        1    IS NOT TRUE  -> FALSE
        1    IS FALSE     -> FALSE
        1    IS NOT FALSE -> TRUE
    """

    def test_is_not_true_includes_null(self, conn):
        """IS NOT TRUE must match NULL and 0 (ids 1, 2)."""
        cur = conn.cursor()
        cur.execute(
            'SELECT id FROM t WHERE flag IS NOT TRUE ORDER BY id'
        )
        assert [r[0] for r in cur.fetchall()] == [1, 2]

    def test_is_true_excludes_null(self, conn):
        """IS TRUE must match only 1 (id 3)."""
        cur = conn.cursor()
        cur.execute('SELECT id FROM t WHERE flag IS TRUE ORDER BY id')
        assert [r[0] for r in cur.fetchall()] == [3]

    def test_is_false_excludes_null(self, conn):
        """IS FALSE must match only 0 (id 2)."""
        cur = conn.cursor()
        cur.execute('SELECT id FROM t WHERE flag IS FALSE ORDER BY id')
        assert [r[0] for r in cur.fetchall()] == [2]

    def test_is_not_false_includes_null(self, conn):
        """IS NOT FALSE must match NULL and 1 (ids 1, 3)."""
        cur = conn.cursor()
        cur.execute(
            'SELECT id FROM t WHERE flag IS NOT FALSE ORDER BY id'
        )
        assert [r[0] for r in cur.fetchall()] == [1, 3]


class TestOldRewriteBroken:
    """Demonstrate that the old !=1 / =1 rewrite is wrong for NULL."""

    def test_old_is_not_true_misses_null(self, conn):
        """Old rewrite: IS NOT TRUE -> !=1.  NULL!=1 is NULL, row lost."""
        cur = conn.cursor()
        cur.execute('SELECT id FROM t WHERE flag !=1 ORDER BY id')
        result = [r[0] for r in cur.fetchall()]
        # Only id=2 (flag=0) matches.  id=1 (NULL) is LOST.
        assert result == [2], (
            'Old rewrite loses NULL rows: got %s instead of [1, 2]' % result
        )

    def test_old_is_not_false_misses_null(self, conn):
        """Old rewrite: IS NOT FALSE -> !=0.  NULL!=0 is NULL, row lost."""
        cur = conn.cursor()
        cur.execute('SELECT id FROM t WHERE flag !=0 ORDER BY id')
        result = [r[0] for r in cur.fetchall()]
        # Only id=3 (flag=1) matches.  id=1 (NULL) is LOST.
        assert result == [3], (
            'Old rewrite loses NULL rows: got %s instead of [1, 3]' % result
        )


class TestFixedRewrite:
    """Verify the corrected rewrite handles NULL properly."""

    def test_fixed_is_not_true(self, conn):
        """Fixed: IS NOT TRUE -> (IS NULL OR !=1)."""
        cur = conn.cursor()
        cur.execute(
            'SELECT id FROM t WHERE (flag IS NULL OR flag !=1) ORDER BY id'
        )
        assert [r[0] for r in cur.fetchall()] == [1, 2]

    def test_fixed_is_true(self, conn):
        """Fixed: IS TRUE -> (IS NOT NULL AND =1)."""
        cur = conn.cursor()
        cur.execute(
            'SELECT id FROM t WHERE (flag IS NOT NULL AND flag =1) ORDER BY id'
        )
        assert [r[0] for r in cur.fetchall()] == [3]

    def test_fixed_is_false(self, conn):
        """Fixed: IS FALSE -> (IS NOT NULL AND =0)."""
        cur = conn.cursor()
        cur.execute(
            'SELECT id FROM t WHERE (flag IS NOT NULL AND flag =0) ORDER BY id'
        )
        assert [r[0] for r in cur.fetchall()] == [2]

    def test_fixed_is_not_false(self, conn):
        """Fixed: IS NOT FALSE -> (IS NULL OR !=0)."""
        cur = conn.cursor()
        cur.execute(
            'SELECT id FROM t WHERE (flag IS NULL OR flag !=0) ORDER BY id'
        )
        assert [r[0] for r in cur.fetchall()] == [1, 3]


class TestAdapterRewrite:
    """Test the actual regex rewrite from gnrsqlite._booleanSubCb."""

    PATTERN = re.compile(r'(\(*)(["\w]["\w.]*) +IS +(NOT +)?(TRUE|FALSE)', re.I)

    @staticmethod
    def _rewrite(m):
        prefix = m.group(1)
        expr = m.group(2)
        is_not = bool(m.group(3))
        is_true = m.group(4).upper() == 'TRUE'
        val = '1' if is_true else '0'
        if is_not:
            return '%s(%s IS NULL OR %s !=%s)' % (prefix, expr, expr, val)
        else:
            return '%s(%s IS NOT NULL AND %s =%s)' % (prefix, expr, expr, val)

    def _apply(self, sql):
        return self.PATTERN.sub(self._rewrite, sql)

    def test_rewrite_is_not_true(self):
        result = self._apply('"t0"."flag" IS NOT TRUE')
        assert result == '("t0"."flag" IS NULL OR "t0"."flag" !=1)'

    def test_rewrite_is_true(self):
        result = self._apply('"t0"."flag" IS TRUE')
        assert result == '("t0"."flag" IS NOT NULL AND "t0"."flag" =1)'

    def test_rewrite_is_false(self):
        result = self._apply('"t0"."flag" IS FALSE')
        assert result == '("t0"."flag" IS NOT NULL AND "t0"."flag" =0)'

    def test_rewrite_is_not_false(self):
        result = self._apply('"t0"."flag" IS NOT FALSE')
        assert result == '("t0"."flag" IS NULL OR "t0"."flag" !=0)'

    def test_rewrite_in_where_clause(self):
        sql = (
            'SELECT * FROM t WHERE ("t0"."__del_ts" IS NULL)'
            ' AND ("t0"."__is_draft" IS NOT TRUE)'
        )
        result = self._apply(sql)
        assert '("t0"."__is_draft" IS NULL OR "t0"."__is_draft" !=1)' in result
        assert '"__del_ts" IS NULL' in result

    def test_rewrite_preserves_null_rows(self, conn):
        """End-to-end: rewritten SQL returns same rows as native IS NOT TRUE."""
        rewritten = self._apply(
            'SELECT id FROM t WHERE flag IS NOT TRUE ORDER BY id'
        )
        cur = conn.cursor()
        cur.execute(rewritten)
        assert [r[0] for r in cur.fetchall()] == [1, 2]

    def test_rewrite_balanced_parentheses(self, conn):
        """Full WHERE clause produces valid SQL after rewrite."""
        sql = (
            'SELECT id FROM t WHERE (flag IS NULL OR flag =0)'
            ' AND (flag IS NOT TRUE) ORDER BY id'
        )
        rewritten = self._apply(sql)
        cur = conn.cursor()
        cur.execute(rewritten)
        rows = [r[0] for r in cur.fetchall()]
        assert rows == [1, 2]
