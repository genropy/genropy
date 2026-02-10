"""Test standalone della logica di condensazione subquery.

Funzione pura: riceve sq_dict e sql_formula, restituisce sq_dict condensato e formula adeguata.
"""
import re


def condense_subqueries(sq_dict, sql_formula):
    """Condensa subquery con stessa (table, where) in un unico entry.

    Args:
        sq_dict: dict {sq_name: {columns, table, where, ...}}
        sql_formula: stringa con #nome riferimenti

    Returns:
        (sq_dict_condensato, formula_adeguata)
    """
    # Raggruppa per (table, where)
    groups = {}
    for sq_name, sq_pars in sq_dict.items():
        key = (sq_pars['table'], sq_pars.get('where'))
        groups.setdefault(key, []).append(sq_name)

    col_counter = 0
    remap = {}  # {absorbed_name: (master_name, col_alias)}

    for key, names in groups.items():
        if len(names) == 1:
            # Singola subquery: assegna c_N alla colonna
            sq_name = names[0]
            sq_pars = sq_dict[sq_name]
            col_alias = 'c_%i' % col_counter
            sq_pars['columns'] = '%s AS %s' % (sq_pars['columns'], col_alias)
            col_counter += 1
            continue

        # Gruppo condensabile: master = primo, assorbi gli altri
        master = names[0]
        master_pars = sq_dict[master]
        merged_cols = []

        for name in names:
            pars = sq_dict[name]
            col_alias = 'c_%i' % col_counter
            merged_cols.append('%s AS %s' % (pars['columns'], col_alias))
            if name != master:
                remap[name] = (master, col_alias)
            else:
                master_col_alias = col_alias
            col_counter += 1

        master_pars['columns'] = ', '.join(merged_cols)

        # Rimuovi assorbiti
        for name in names[1:]:
            del sq_dict[name]

    # Adegua la formula
    for absorbed, (master, col_alias) in remap.items():
        sql_formula = re.sub(r'#%s\b' % absorbed, '%s.%s' % (master, col_alias), sql_formula)

    # Sostituisci i riferimenti rimasti (non assorbiti) con nome.c_N
    for sq_name, sq_pars in sq_dict.items():
        # Estrai il primo c_N dalle colonne
        m = re.search(r'AS (c_\d+)', sq_pars['columns'])
        if m:
            first_col = m.group(1)
            sql_formula = re.sub(r'#%s\b' % sq_name, '%s.%s' % (sq_name, first_col), sql_formula)

    return sq_dict, sql_formula


# ============================================================
# TEST
# ============================================================

class TestCondensation:

    def test_no_condensation_different_where(self):
        """Due subquery con where diversa: nessuna condensazione."""
        sq_dict = {
            'total': {'columns': 'COUNT(*)', 'table': 'fatt.fattura',
                      'where': '$cliente_id=#THIS.id'},
            'available': {'columns': 'COUNT(*)', 'table': 'fatt.fattura',
                          'where': '$cliente_id=#THIS.id AND $available=:avail'},
        }
        formula = '#total || :sep || #available'

        result, new_formula = condense_subqueries(sq_dict, formula)

        # Entrambe presenti, nessuna assorbita
        assert 'total' in result
        assert 'available' in result
        assert 'total.c_0' in new_formula
        assert 'available.c_1' in new_formula

    def test_condensation_same_table_where(self):
        """Due subquery con stessa table+where: condensazione."""
        sq_dict = {
            'nfat': {'columns': 'COUNT(*)', 'table': 'fatt.fattura',
                     'where': '$cliente_id=#THIS.id'},
            'valfat': {'columns': 'SUM($totale_fattura)', 'table': 'fatt.fattura',
                       'where': '$cliente_id=#THIS.id'},
        }
        formula = '#nfat || :sep || #valfat'

        result, new_formula = condense_subqueries(sq_dict, formula)

        # Solo nfat resta (master), valfat assorbita
        assert 'nfat' in result
        assert 'valfat' not in result
        # Colonne fuse
        assert 'COUNT(*) AS c_0' in result['nfat']['columns']
        assert 'SUM($totale_fattura) AS c_1' in result['nfat']['columns']
        # Formula adeguata
        assert 'nfat.c_0' in new_formula
        assert 'nfat.c_1' in new_formula
        assert '#' not in new_formula

    def test_single_subquery(self):
        """Una sola subquery: nessuna condensazione, alias c_0."""
        sq_dict = {
            'dflt': {'columns': 'COUNT(*)', 'table': 'fatt.fattura',
                     'where': '$cliente_id=#THIS.id'},
        }
        formula = '#dflt'

        result, new_formula = condense_subqueries(sq_dict, formula)

        assert 'dflt' in result
        assert result['dflt']['columns'] == 'COUNT(*) AS c_0'
        assert new_formula == 'dflt.c_0'

    def test_single_subquery_in_coalesce(self):
        """Una sola subquery dentro COALESCE."""
        sq_dict = {
            'dflt': {'columns': 'COUNT(*)', 'table': 'fatt.fattura',
                     'where': '$cliente_id=#THIS.id'},
        }
        formula = 'COALESCE(#dflt, 0)'

        result, new_formula = condense_subqueries(sq_dict, formula)

        assert new_formula == 'COALESCE(dflt.c_0, 0)'

    def test_three_subqueries_two_condensable(self):
        """Tre subquery: due condensabili, una no."""
        sq_dict = {
            'nfat': {'columns': 'COUNT(*)', 'table': 'fatt.fattura',
                     'where': '$cliente_id=#THIS.id'},
            'valfat': {'columns': 'SUM($totale_fattura)', 'table': 'fatt.fattura',
                       'where': '$cliente_id=#THIS.id'},
            'nfat2014': {'columns': 'COUNT(*)', 'table': 'fatt.fattura',
                         'where': "$cliente_id=#THIS.id AND $data>='2014-01-01'"},
        }
        formula = '#nfat || :s1 || #valfat || :s2 || #nfat2014'

        result, new_formula = condense_subqueries(sq_dict, formula)

        # nfat e valfat condensati, nfat2014 separato
        assert 'nfat' in result
        assert 'valfat' not in result
        assert 'nfat2014' in result
        assert 'nfat.c_0' in new_formula
        assert 'nfat.c_1' in new_formula
        assert 'nfat2014.c_2' in new_formula

    def test_no_subqueries(self):
        """Dict vuoto: nessun crash."""
        sq_dict = {}
        formula = 'UPPER($title)'

        result, new_formula = condense_subqueries(sq_dict, formula)

        assert result == {}
        assert new_formula == 'UPPER($title)'

    def test_formula_with_existing_qualified_ref(self):
        """Formula che ha gia un riferimento qualificato #nome_colonna."""
        sq_dict = {
            'dflt': {'columns': 'COUNT(*)', 'table': 'fatt.fattura',
                     'where': '$cliente_id=#THIS.id'},
        }
        # Utente scrive #dflt_c_0 esplicitamente
        formula = 'COALESCE(#dflt_c_0, 0)'

        result, new_formula = condense_subqueries(sq_dict, formula)

        # #dflt NON deve matchare dentro #dflt_c_0 (word boundary)
        # #dflt\b non matcha #dflt_c_0 perche _ e un word char
        assert '#dflt_c_0' in new_formula  # resta invariato
