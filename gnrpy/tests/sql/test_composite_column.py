"""Runtime tests for compositeColumn and composite-key JOINs.

Tests run real queries against both PostgreSQL (test_invoice_pg) and
SQLite (test_invoice), verifying that:
- compositeColumn generates correct JSON-array values
- composite-key JOINs return correct data
- navigation through composite keys resolves to correct columns
- deep navigation (composite -> further relation) works
- WHERE and ORDER BY on composite-navigated columns work
"""

import pytest
from gnr.app.gnrapp import GnrApp


INSTANCE_PATH_PG = (
    '/Users/gporcari/Sviluppo/Genropy/genropy'
    '/projects/test_invoice/instances/test_invoice_pg'
)
INSTANCE_PATH_SQLITE = (
    '/Users/gporcari/Sviluppo/Genropy/genropy'
    '/projects/test_invoice/instances/test_invoice'
)


@pytest.fixture(scope='module')
def db_pg():
    try:
        app = GnrApp(INSTANCE_PATH_PG)
        return app.db
    except Exception:
        pytest.skip('PostgreSQL instance not available')


@pytest.fixture(scope='module')
def db_sqlite():
    try:
        app = GnrApp(INSTANCE_PATH_SQLITE)
        return app.db
    except Exception:
        pytest.skip('SQLite instance not available')


# ===================================================================
# PostgreSQL tests
# ===================================================================

class TestCompositeColumnPg:

    def test_composite_value_format(self, db_pg):
        """compositeColumn produces a JSON-array string with the component values."""
        row = db_pg.table('invc.price_year').query(
            columns='$product_year_key, $product_id, $year',
            limit=1
        ).fetch()[0]
        key = row['product_year_key']
        assert key.startswith('[')
        assert key.endswith(']')
        assert str(row['year']) in key

    def test_composite_join_returns_data(self, db_pg):
        """Navigation via composite key returns real data from target table."""
        rows = db_pg.table('invc.price_year_note').query(
            columns='$note_text, $price_year_price',
            limit=5
        ).fetch()
        assert len(rows) > 0
        for r in rows:
            assert r['price_year_price'] is not None
            assert float(r['price_year_price']) > 0

    def test_composite_join_matches_source(self, db_pg):
        """Price navigated via composite key matches the actual price_year record."""
        row = db_pg.table('invc.price_year_note').query(
            columns='$product_id, $year, $price_year_price',
            limit=1
        ).fetch()[0]
        direct = db_pg.table('invc.price_year').query(
            columns='$unit_price',
            where='$product_id = :pid AND $year = :y',
            pid=row['product_id'], y=row['year']
        ).fetch()[0]
        assert float(row['price_year_price']) == float(direct['unit_price'])

    def test_composite_deep_navigation(self, db_pg):
        """Deep navigation: composite key -> price_year -> product.description."""
        rows = db_pg.table('invc.price_year_note').query(
            columns='$product_id, $product_description',
            limit=5
        ).fetch()
        assert len(rows) > 0
        for r in rows:
            assert r['product_description'] is not None
            direct = db_pg.table('invc.product').query(
                columns='$description',
                where='$id = :pid', pid=r['product_id']
            ).fetch()[0]
            assert r['product_description'] == direct['description']

    def test_composite_formula_navigation(self, db_pg):
        """Navigation to formulaColumn on target via composite key."""
        row = db_pg.table('invc.price_year_note').query(
            columns='$year, $price_year_price, $price_year_label',
            limit=1
        ).fetch()[0]
        label = row['price_year_label']
        assert str(row['year']) in label
        assert str(row['price_year_price']) in label

    def test_composite_where_filters(self, db_pg):
        """WHERE on column navigated via composite key filters correctly."""
        total = db_pg.table('invc.price_year_note').query(
            columns='$id'
        ).count()
        filtered = db_pg.table('invc.price_year_note').query(
            columns='$id',
            where='$price_year_price > :val', val=500
        ).count()
        assert 0 < filtered < total

    def test_composite_order_by(self, db_pg):
        """ORDER BY on column navigated via composite key orders correctly."""
        rows = db_pg.table('invc.price_year_note').query(
            columns='$note_text, $price_year_price',
            order_by='$price_year_price ASC',
            limit=10
        ).fetch()
        prices = [float(r['price_year_price']) for r in rows]
        assert prices == sorted(prices)

    def test_composite_count_matches(self, db_pg):
        """Total price_year_note count is consistent."""
        count = db_pg.table('invc.price_year_note').query(
            columns='$id'
        ).count()
        assert count == 3381


# ===================================================================
# SQLite tests
# ===================================================================

class TestCompositeColumnSqlite:

    def test_composite_value_format(self, db_sqlite):
        """compositeColumn produces a JSON-array string."""
        row = db_sqlite.table('invc.price_year').query(
            columns='$product_year_key, $product_id, $year',
            limit=1
        ).fetch()[0]
        key = row['product_year_key']
        assert key.startswith('[')
        assert key.endswith(']')
        assert str(row['year']) in key

    def test_composite_join_returns_data(self, db_sqlite):
        """Navigation via composite key returns real data."""
        rows = db_sqlite.table('invc.price_year_note').query(
            columns='$note_text, $price_year_price',
            limit=5
        ).fetch()
        assert len(rows) > 0
        for r in rows:
            assert r['price_year_price'] is not None

    def test_composite_join_matches_source(self, db_sqlite):
        """Price via composite key matches actual price_year record."""
        row = db_sqlite.table('invc.price_year_note').query(
            columns='$product_id, $year, $price_year_price',
            limit=1
        ).fetch()[0]
        direct = db_sqlite.table('invc.price_year').query(
            columns='$unit_price',
            where='$product_id = :pid AND $year = :y',
            pid=row['product_id'], y=row['year']
        ).fetch()[0]
        assert float(row['price_year_price']) == float(direct['unit_price'])

    def test_composite_deep_navigation(self, db_sqlite):
        """Deep navigation through composite key to product."""
        rows = db_sqlite.table('invc.price_year_note').query(
            columns='$product_id, $product_description',
            limit=5
        ).fetch()
        assert len(rows) > 0
        for r in rows:
            assert r['product_description'] is not None

    def test_composite_where_filters(self, db_sqlite):
        """WHERE on composite-navigated column filters correctly."""
        total = db_sqlite.table('invc.price_year_note').query(
            columns='$id'
        ).count()
        filtered = db_sqlite.table('invc.price_year_note').query(
            columns='$id',
            where='$price_year_price > :val', val=500
        ).count()
        assert 0 < filtered < total

    def test_composite_order_by(self, db_sqlite):
        """ORDER BY on composite-navigated column orders correctly."""
        rows = db_sqlite.table('invc.price_year_note').query(
            columns='$note_text, $price_year_price',
            order_by='$price_year_price ASC',
            limit=10
        ).fetch()
        prices = [float(r['price_year_price']) for r in rows]
        assert prices == sorted(prices)
