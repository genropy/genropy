# GEP 2 — `manyRelation`: filtered many-side relations declared on the one-side table

| | |
|---|---|
| **Area** | sql |
| **Status** | Draft |
| **Author** | Giovanni Porcari |
| **Created** | 2026-09-20 |
| **Refs** | GEP 1, #1354 |

## 1. Abstract

Today the many-side relations of a table exist only as the automatic inverse
of a `relation()` declared on the FK column of the other table: `customer`
gets `@invoices` because `invoice.customer_id` points to it. This GEP adds
`manyRelation()` on the **one-side** table to declare further many-side
relations by hand, each one a filtered branch of an automatic one:

```python
# in customer
tbl.manyRelation('invoices_current_year', '@invoices', condition='$year = :env_current_year')
tbl.manyRelation('invoices_prev_year', '@invoices', condition='$year = :env_current_year - 1')
tbl.manyRelation('last_invoice', '@invoices', condition='$is_last IS TRUE', one_one=True)
```

Its purpose is to become the **only** way to attach a condition to a join,
and to deprecate the ways that exist today.

## 2. Current state

Conditions on joins are expressed today in three unrelated places:

| mechanism | where | note |
|---|---|---|
| `cnd`, `join_on`, `between` attributes of `relation()` | `gnrsqlmodel/model.py` `addRelation`; `gnrsqldata/compiler.py` join ON | model level, per FK; `between` is already marked for deprecation in the compiler; no usage of `cnd` / `join_on` found in the indexed repositories |
| `joinConditions`, `setJoinCondition`, `sqlContextName` | page; `apphandler._joinConditionsFromContext`; `compiler.py` `getJoinCondition` | query time, from the page; keyed by relation name; the `jc_kwargs` parsing in `gnrsqldata/query.py` is known to be broken |
| `relationContext` (planned widget) | page | never built |

None of them gives the filtered relation a **name**: the filter is attached to
the join of an existing relation, so it cannot appear in the fields tree,
cannot be reused across queries and cannot carry aggregates.

## 3. Proposal

`manyRelation(name, relation, condition=None, one_one=False, **kwargs)` on
the table source (`tbl`), next to `column()`, `formulaColumn()`,
`aliasColumn()`.

- `relation` is an existing many-side relation of the table (`'@invoices'`).
- Each call registers one more relation node on the table (`mode='M'`, same
  one/many columns as the base relation, plus the condition and `one_one`).
- The fields tree shows it as an `RM` node (or `RO` with `one_one`), already
  filtered, with the aggregate leaves of GEP 1 like any other relation.
- The compiler puts the condition in the ON of the join (path grammar) and in
  the WHERE of the correlated subquery (GEP 1 grammar).
- Parameters follow the `:env_*` convention already used by formulas.

With this, GEP 1 needs no filter syntax: `@invoices_prev_year.sum($total)`.

### 3.1 Hypothesis: parametrised relations with `ask`

A manual relation can carry `ask`, like a `formulaColumn` does today, so the
user fixes the parameter when dropping a leaf from that node:

```python
tbl.manyRelation('invoices_year', '@invoices', condition='$year = :year',
                 ask=dict(title='Year', fields=[dict(name='year', dtype='I', lbl='Year')]),
                 name_long='Invoices $year')
```

Dropping `@invoices_year.sum($total)` asks for the year and produces
"Invoices 2021 / sum total" without any declaration for 2021 in the model.
The value travels with the cell through the existing `formulaVariant`
channel (`var_year`, `fieldname` / `header` templates, `getVirtualColumn`
override), so two cells with different years coexist in one grid.

## 4. Transition

- The declaration in the model is harmless by itself: without a consumer the
  extra node is inert. It can be delivered as an ordinary PR.
- The condition is handled by the new compiler of GEP 1 (section 8). The
  legacy compiler handles it only if the change is limited to the point where
  `joinExtra['condition']` enters the ON clause today; otherwise the legacy
  compiler ignores manual relations.
- Deprecation of `cnd` / `join_on` / `between` and of the query-time
  `joinConditions` family follows an inventory of their real usages in the
  indexed repositories, with a migration for each.

## 5. Open points

- Arguments of `manyRelation` beyond `condition` and `one_one` (order,
  group in the tree, `name_long`).
- Whether a manual relation can derive from another manual relation.
- Interaction with `joinConditions` given at query time on the same node
  during the transition.
- Query-time conditions whose values are known only on the page: whether
  `manyRelation` with `:env_*` parameters and `ask` covers every case found
  in the inventory.
