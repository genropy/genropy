"""Smoke test: verify we can load the instance and query the db."""


def test_app_loads(app):
    assert app is not None
    assert app.db is not None


def test_customer_count(db):
    count = db.table('invc.customer').query().count()
    assert count > 0, 'Expected at least one customer'


def test_invoice_count(db):
    count = db.table('invc.invoice').query().count()
    assert count > 0, 'Expected at least one invoice'


def test_product_count(db):
    count = db.table('invc.product').query().count()
    assert count > 0, 'Expected at least one product'


def test_customer_has_formula_columns(db):
    """Verify existing formulaColumn n_invoices works."""
    result = db.table('invc.customer').query(
        columns='$account_name,$n_invoices',
        limit=5,
        order_by='$n_invoices DESC'
    ).fetch()
    assert len(result) > 0
    assert result[0]['n_invoices'] > 0
