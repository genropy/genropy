"""Test SqlCompoundQuery con dataset invoice reale.

Testa UNION, UNION ALL, INTERSECT, EXCEPT con 3200 customers,
60K invoices, 410K invoice_row su PostgreSQL.

Eseguire con:  pytest test_compound_query.py -v -s
"""


class TestCompoundQueryBasic:
    """Test base: UNION, UNION ALL, INTERSECT, EXCEPT."""

    def test_union_customers_by_state(self, db):
        """Clienti NSW UNION clienti VIC — testa mangling parametri omonimi."""
        q_nsw = db.query('invc.customer', columns='$account_name,$state',
                         where='$state = :st', st='NSW')
        q_vic = db.query('invc.customer', columns='$account_name,$state',
                         where='$state = :st', st='VIC')
        result = (q_nsw + q_vic).fetch()
        n_nsw = q_nsw.count()
        n_vic = q_vic.count()
        assert len(result) == n_nsw + n_vic
        states = {r['state'] for r in result}
        assert states == {'NSW', 'VIC'}

    def test_union_all_same_query(self, db):
        """UNION ALL della stessa query: deve raddoppiare le righe."""
        q1 = db.query('invc.customer', columns='$account_name',
                      where='$state = :st', st='NSW')
        q2 = db.query('invc.customer', columns='$account_name',
                      where='$state = :st', st='NSW')
        result = (q1 | q2).fetch()
        n = q1.count()
        assert len(result) == n * 2

    def test_intersect_high_volume_high_value(self, db):
        """Clienti con >20 fatture INTERSECT clienti con total > 30K."""
        q_many = db.query('invc.customer', columns='$id,$account_name',
                          where='$n_invoices > :min_n', min_n=20)
        q_rich = db.query('invc.customer', columns='$id,$account_name',
                          where='$invoiced_total > :min_t', min_t=30000)
        result = (q_many & q_rich).fetch()
        assert len(result) > 0
        for row in result:
            cust = db.query('invc.customer', columns='$n_invoices,$invoiced_total',
                            where='$id = :id', id=row['id']).fetch()[0]
            assert cust['n_invoices'] > 20
            assert cust['invoiced_total'] > 30000

    def test_except_exclude_state(self, db):
        """Tutti i clienti EXCEPT quelli di NSW."""
        q_all = db.query('invc.customer', columns='$id,$account_name,$state')
        q_nsw = db.query('invc.customer', columns='$id,$account_name,$state',
                         where='$state = :st', st='NSW')
        result = (q_all - q_nsw).fetch()
        states = {r['state'] for r in result}
        assert 'NSW' not in states
        assert len(result) == q_all.count() - q_nsw.count()


class TestCompoundQueryAdvanced:
    """Test avanzati: cross-table, chaining, parentesi."""

    def test_union_cross_table(self, db):
        """Top product per customer UNION top product per state."""
        q_cust = db.query('invc.customer', columns='$top_product_id',
                          where='$state = :st', st='NSW')
        q_state = db.query('invc.state', columns='$top_product_id')
        result = (q_cust + q_state).fetch()
        assert len(result) > 0

    def test_chain_three_states(self, db):
        """NSW + VIC + QLD — chaining a 3 query con stesso parametro."""
        q1 = db.query('invc.customer', columns='$account_name,$state',
                      where='$state = :st', st='NSW')
        q2 = db.query('invc.customer', columns='$account_name,$state',
                      where='$state = :st', st='VIC')
        q3 = db.query('invc.customer', columns='$account_name,$state',
                      where='$state = :st', st='QLD')
        result = (q1 + q2 + q3).fetch()
        states = {r['state'] for r in result}
        assert states == {'NSW', 'VIC', 'QLD'}
        assert len(result) == q1.count() + q2.count() + q3.count()

    def test_parentheses_intersect_unions(self, db):
        """(NSW + VIC) INTERSECT (NSW attivi + VIC attivi)."""
        q_nsw = db.query('invc.customer', columns='$id,$account_name',
                         where='$state = :st', st='NSW')
        q_vic = db.query('invc.customer', columns='$id,$account_name',
                         where='$state = :st', st='VIC')
        q_nsw_active = db.query('invc.customer', columns='$id,$account_name',
                                where='$state = :st AND $n_invoices > :min_n',
                                st='NSW', min_n=10)
        q_vic_active = db.query('invc.customer', columns='$id,$account_name',
                                where='$state = :st AND $n_invoices > :min_n',
                                st='VIC', min_n=10)
        result = ((q_nsw + q_vic) & (q_nsw_active + q_vic_active)).fetch()
        expected = (q_nsw_active + q_vic_active).fetch()
        assert len(result) == len(expected)

    def test_compound_count(self, db):
        """Verifica coerenza tra .count() e len(.fetch())."""
        q1 = db.query('invc.customer', columns='$account_name',
                      where='$state = :st', st='NSW')
        q2 = db.query('invc.customer', columns='$account_name',
                      where='$state = :st', st='VIC')
        compound = q1 + q2
        assert compound.count() == len(compound.fetch())


class TestCompoundQueryWithFormulas:
    """Test con formulaColumn e sq_join."""

    def test_union_with_formula_columns(self, db):
        """UNION con formulaColumn e sq_join abilitato."""
        q1 = db.query('invc.customer', columns='$account_name,$n_invoices',
                      where='$state = :st', st='NSW', enable_sq_join=True)
        q2 = db.query('invc.customer', columns='$account_name,$n_invoices',
                      where='$state = :st', st='VIC', enable_sq_join=True)
        result = (q1 + q2).fetch()
        assert len(result) > 0
        for row in result:
            assert row['n_invoices'] is not None

    def test_except_inactive_customers(self, db):
        """Clienti attivi 2023 EXCEPT clienti attivi 2024 (churn analysis)."""
        q_2023 = db.query('invc.customer', columns='$id,$account_name',
                          where='$n_invoices_2023 > :min_n', min_n=0)
        q_2024 = db.query('invc.customer', columns='$id,$account_name',
                          where='$n_invoices_2024 > :min_n', min_n=0)
        lost = (q_2023 - q_2024).fetch()
        for row in lost:
            c = db.query('invc.customer', columns='$n_invoices_2024',
                         where='$id = :id', id=row['id']).fetch()[0]
            assert (c['n_invoices_2024'] or 0) == 0
