#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for SqlCompoundQuery — UNION, INTERSECT, EXCEPT via Python operators.

Uses the standard video test database with movie, dvd, cast, people tables.

Movie data reference (11 movies, id 0..10):
    id=0  Match point        year=2005  genre=DRAMA      nationality=USA,UK
    id=1  Scoop              year=2006  genre=COMEDY     nationality=USA,UK
    id=2  Munich             year=2005  genre=DRAMA      nationality=USA
    id=3  Saving private Ryan year=1998 genre=WAR        nationality=USA
    id=4  Eyes wide shut     year=1999  genre=DRAMA      nationality=UK
    id=5  Barry Lindon       year=1975  genre=DRAMA      nationality=UK
    id=6  Scarface           year=1983  genre=CRIME      nationality=USA
    id=7  The untouchables   year=1987  genre=CRIME      nationality=USA
    id=8  Psycho             year=1960  genre=THRILLER   nationality=UK
    id=9  The Aviator        year=2004  genre=BIOGRAPHY  nationality=USA
    id=10 The Departed       year=2006  genre=CRIME      nationality=USA
"""

from gnr.sql.gnrsql import GnrSqlDb
from gnr.sql.gnrsqldata import SqlCompoundQuery

from .common import BaseGnrSqlTest, configureDb


class BaseCompoundQuery(BaseGnrSqlTest):
    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.init()
        cls.db.createDb(cls.dbname)
        configureDb(cls.db)
        cls.db.startup()
        cls.db.checkDb(applyChanges=True)
        cls.db.importXmlData(cls.SAMPLE_XMLDATA)
        cls.db.commit()

    @classmethod
    def teardown_class(cls):
        cls.db.closeConnection()
        cls.db.dropDb(cls.dbname)

    # -- helpers --

    def _movie_query(self, **kwargs):
        return self.db.query('video.movie', columns='$id,$title,$year,$genre,$nationality', **kwargs)

    def _ids(self, compound_q):
        """Execute a compound query and return sorted list of movie ids."""
        rows = self.db.execute(compound_q.sqltext, compound_q.sqlparams,
                               dbtable='video.movie').fetchall()
        return sorted(r[0] for r in rows)

    def _id_list(self, compound_q):
        """Execute and return ids preserving order (with duplicates)."""
        rows = self.db.execute(compound_q.sqltext, compound_q.sqlparams,
                               dbtable='video.movie').fetchall()
        return [r[0] for r in rows]

    # ================================================================
    # 1. UNION (+) — removes duplicates
    # ================================================================

    def test_union_basic(self):
        """UNION of year=2005 and year=2006 gives 4 distinct movies."""
        q1 = self._movie_query(where='$year=:y', y=2005)
        q2 = self._movie_query(where='$year=:y', y=2006)
        cq = q1 + q2
        assert isinstance(cq, SqlCompoundQuery)
        ids = self._ids(cq)
        assert set(ids) == {0, 1, 2, 10}

    def test_union_removes_duplicates(self):
        """UNION with overlapping sets removes duplicates."""
        q1 = self._movie_query(where="$genre=:g", g='DRAMA')
        q2 = self._movie_query(where='$year=:y', y=2005)
        cq = q1 + q2
        ids = self._ids(cq)
        # DRAMA: {0,2,4,5} ∪ year2005: {0,2} → {0,2,4,5}
        assert set(ids) == {0, 2, 4, 5}

    # ================================================================
    # 2. UNION ALL (|) — keeps duplicates
    # ================================================================

    def test_union_all_basic(self):
        """UNION ALL of year=2005 and year=2006 gives 4 rows (no overlap)."""
        q1 = self._movie_query(where='$year=:y', y=2005)
        q2 = self._movie_query(where='$year=:y', y=2006)
        cq = q1 | q2
        assert isinstance(cq, SqlCompoundQuery)
        assert cq.count() == 4

    def test_union_all_keeps_duplicates(self):
        """UNION ALL with overlapping sets keeps duplicate rows."""
        q1 = self._movie_query(where="$genre=:g", g='DRAMA')
        q2 = self._movie_query(where='$year=:y', y=2005)
        cq = q1 | q2
        all_ids = self._id_list(cq)
        # DRAMA: 4 rows + year2005: 2 rows = 6 total
        assert len(all_ids) == 6

    # ================================================================
    # 3. INTERSECT (&) — only common rows
    # ================================================================

    def test_intersect_basic(self):
        """INTERSECT of DRAMA and year=2005 gives only dramas from 2005."""
        q1 = self._movie_query(where="$genre=:g", g='DRAMA')
        q2 = self._movie_query(where='$year=:y', y=2005)
        cq = q1 & q2
        assert isinstance(cq, SqlCompoundQuery)
        ids = self._ids(cq)
        # DRAMA ∩ year2005: Match point (0) and Munich (2)
        assert set(ids) == {0, 2}

    def test_intersect_empty(self):
        """INTERSECT of disjoint sets gives 0 rows."""
        q1 = self._movie_query(where="$genre=:g", g='COMEDY')
        q2 = self._movie_query(where='$year=:y', y=2005)
        cq = q1 & q2
        assert cq.count() == 0

    # ================================================================
    # 4. EXCEPT (-) — set difference
    # ================================================================

    def test_except_basic(self):
        """EXCEPT removes rows present in second query."""
        q1 = self._movie_query(where="$genre=:g", g='DRAMA')
        q2 = self._movie_query(where='$year=:y', y=2005)
        cq = q1 - q2
        ids = self._ids(cq)
        # DRAMA\year2005: {0,2,4,5} \ {0,2} → {4,5}
        assert set(ids) == {4, 5}

    def test_except_all_removed(self):
        """EXCEPT where second set contains all of first gives 0 rows."""
        q1 = self._movie_query(where='$year=:y', y=2005)
        q2 = self._movie_query(where="$genre=:g", g='DRAMA')
        cq = q1 - q2
        # year2005={0,2} both DRAMA → empty
        assert cq.count() == 0

    # ================================================================
    # 5. Chains of 3 queries
    # ================================================================

    def test_chain_three_union(self):
        """q1 + q2 + q3 chains three UNION operations."""
        q1 = self._movie_query(where='$year=:y', y=2005)
        q2 = self._movie_query(where='$year=:y', y=2006)
        q3 = self._movie_query(where='$year=:y', y=1999)
        cq = q1 + q2 + q3
        ids = self._ids(cq)
        assert set(ids) == {0, 1, 2, 4, 10}

    def test_chain_mixed_operators(self):
        """(q1 + q2) - q3 removes from a union."""
        q1 = self._movie_query(where='$year=:y', y=2005)
        q2 = self._movie_query(where='$year=:y', y=2006)
        q3 = self._movie_query(where="$genre=:g", g='DRAMA')
        cq = (q1 + q2) - q3
        ids = self._ids(cq)
        # {0,1,2,10} \ {0,2,4,5} → {1,10}
        assert set(ids) == {1, 10}

    # ================================================================
    # 6. Parentheses change evaluation order
    # ================================================================

    def test_parentheses_union_then_except(self):
        """(DRAMA + CRIME) - year2005 gives different result than DRAMA + (CRIME - year2005)."""
        # Case A: (DRAMA + CRIME) - year2005
        q1a = self._movie_query(where="$genre=:g", g='DRAMA')
        q2a = self._movie_query(where="$genre=:g", g='CRIME')
        q3a = self._movie_query(where='$year=:y', y=2005)
        cq_a = (q1a + q2a) - q3a
        ids_a = set(self._ids(cq_a))
        # DRAMA∪CRIME = {0,2,4,5,6,7,10}, minus year2005={0,2} → {4,5,6,7,10}
        assert ids_a == {4, 5, 6, 7, 10}

        # Case B: DRAMA + (CRIME - year2005)
        q1b = self._movie_query(where="$genre=:g", g='DRAMA')
        q2b = self._movie_query(where="$genre=:g", g='CRIME')
        q3b = self._movie_query(where='$year=:y', y=2005)
        cq_b = q1b + (q2b - q3b)
        ids_b = set(self._ids(cq_b))
        # CRIME\year2005 = {6,7,10} (no CRIME in 2005), DRAMA∪{6,7,10} = {0,2,4,5,6,7,10}
        assert ids_b == {0, 2, 4, 5, 6, 7, 10}

        assert ids_a != ids_b

    # ================================================================
    # 7. Mangler — same param names, different values
    # ================================================================

    def test_mangler_different_values(self):
        """Two queries with same param name :y but different values produce correct results."""
        q1 = self._movie_query(where='$year=:y', y=2005)
        q2 = self._movie_query(where='$year=:y', y=1960)
        cq = q1 + q2
        ids = self._ids(cq)
        # year2005={0,2} ∪ year1960={8}
        assert set(ids) == {0, 2, 8}

    def test_mangler_same_param_name_three_queries(self):
        """Three queries all using :y with different values."""
        q1 = self._movie_query(where='$year=:y', y=2005)
        q2 = self._movie_query(where='$year=:y', y=2006)
        q3 = self._movie_query(where='$year=:y', y=1960)
        cq = q1 + q2 + q3
        ids = self._ids(cq)
        assert set(ids) == {0, 1, 2, 8, 10}

    def test_mangler_mixed_param_names(self):
        """Two queries with different param names don't interfere."""
        q1 = self._movie_query(where='$year=:y', y=2005)
        q2 = self._movie_query(where="$genre=:g", g='CRIME')
        cq = q1 + q2
        ids = self._ids(cq)
        # year2005={0,2} ∪ CRIME={6,7,10}
        assert set(ids) == {0, 2, 6, 7, 10}

    # ================================================================
    # 8. count() method
    # ================================================================

    def test_count_union(self):
        q1 = self._movie_query(where='$year=:y', y=2005)
        q2 = self._movie_query(where='$year=:y', y=2006)
        cq = q1 + q2
        assert cq.count() == 4

    def test_count_intersect(self):
        q1 = self._movie_query(where="$genre=:g", g='DRAMA')
        q2 = self._movie_query(where='$year=:y', y=2005)
        cq = q1 & q2
        assert cq.count() == 2

    def test_count_except(self):
        q1 = self._movie_query(where="$genre=:g", g='DRAMA')
        q2 = self._movie_query(where='$year=:y', y=2005)
        cq = q1 - q2
        assert cq.count() == 2

    def test_count_chain(self):
        q1 = self._movie_query(where='$year=:y', y=2005)
        q2 = self._movie_query(where='$year=:y', y=2006)
        q3 = self._movie_query(where='$year=:y', y=1999)
        cq = q1 + q2 + q3
        assert cq.count() == 5

    # ================================================================
    # 9. CompoundQuery + SqlQuery
    # ================================================================

    def test_compound_plus_simple(self):
        """(q1 + q2) + q3 — compound extended with a simple query."""
        q1 = self._movie_query(where='$year=:y', y=2005)
        q2 = self._movie_query(where='$year=:y', y=2006)
        q3 = self._movie_query(where='$year=:y', y=1960)
        cq = (q1 + q2) + q3
        assert isinstance(cq, SqlCompoundQuery)
        ids = self._ids(cq)
        assert set(ids) == {0, 1, 2, 8, 10}

    def test_compound_minus_simple(self):
        """(q1 | q2) - q3 — except a simple query from a compound."""
        q1 = self._movie_query(where='$year=:y', y=2005)
        q2 = self._movie_query(where='$year=:y', y=2006)
        q3 = self._movie_query(where="$genre=:g", g='DRAMA')
        cq = (q1 | q2) - q3
        ids = self._ids(cq)
        # UNION ALL(2005,2006)={0,2,1,10} EXCEPT DRAMA={0,2,4,5} → {1,10}
        assert set(ids) == {1, 10}

    # ================================================================
    # 10. CompoundQuery + CompoundQuery
    # ================================================================

    def test_compound_plus_compound(self):
        """(q1 + q2) + (q3 + q4) merges two compound queries."""
        q1 = self._movie_query(where='$year=:y', y=2005)
        q2 = self._movie_query(where='$year=:y', y=2006)
        q3 = self._movie_query(where='$year=:y', y=1960)
        q4 = self._movie_query(where='$year=:y', y=1975)
        cq = (q1 + q2) + (q3 + q4)
        assert isinstance(cq, SqlCompoundQuery)
        ids = self._ids(cq)
        # {0,2} ∪ {1,10} ∪ {8} ∪ {5}
        assert set(ids) == {0, 1, 2, 5, 8, 10}

    def test_compound_intersect_compound(self):
        """(DRAMA | CRIME) & (UK | USA) — intersect of two compound queries."""
        q1 = self._movie_query(where="$genre=:g", g='DRAMA')
        q2 = self._movie_query(where="$genre=:g", g='CRIME')
        q3 = self._movie_query(where="$nationality=:n", n='UK')
        q4 = self._movie_query(where="$nationality=:n", n='USA')
        cq = (q1 | q2) & (q3 | q4)
        ids = self._ids(cq)
        # DRAMA|CRIME (all): {0,2,4,5,6,7,10}
        # UK|USA (exact match): UK={4,5,8}, USA={2,3,6,7,9,10}
        # intersection: {2,4,5,6,7,10}
        assert set(ids) == {2, 4, 5, 6, 7, 10}


# ================================================================
# Backend-specific test classes
# ================================================================

class TestCompoundQuery_sqlite(BaseCompoundQuery):
    @classmethod
    def init(cls):
        cls.name = 'sqlite'
        cls.dbname = cls.CONFIG['db.sqlite?filename']
        cls.db = GnrSqlDb(dbname=cls.dbname)


class TestCompoundQuery_postgres(BaseCompoundQuery):
    @classmethod
    def init(cls):
        cls.name = 'postgres'
        cls.dbname = 'test_compound'
        cls.db = GnrSqlDb(implementation='postgres',
                          host=cls.pg_conf.get("host"),
                          port=cls.pg_conf.get("port"),
                          dbname=cls.dbname,
                          user=cls.pg_conf.get("user"),
                          password=cls.pg_conf.get("password"))


class TestCompoundQuery_postgres3(BaseCompoundQuery):
    @classmethod
    def init(cls):
        cls.name = 'postgres3'
        cls.dbname = 'test_compound'
        cls.db = GnrSqlDb(implementation='postgres3',
                          host=cls.pg_conf.get("host"),
                          port=cls.pg_conf.get("port"),
                          dbname=cls.dbname,
                          user=cls.pg_conf.get("user"),
                          password=cls.pg_conf.get("password"))
