# GEP 1 — Relation functions in the column grammar

| | |
|---|---|
| **Area** | sql |
| **Status** | Draft |
| **Author** | Giovanni Porcari |
| **Created** | 2026-09-20 |
| **Refs** | #1354, #623, #544, #496, #617 |
| **Branch** | `feature/1354-relation-aggregates` (this document; implementation follows section 8) |

## 1. Abstract

This GEP proposes an extension of the GenroPy column grammar: a function
applied to a relation path, e.g. `@invoices.sum($total)`, `@invoices.count()`,
`@invoices.@rows.count(distinct($product_id))`. Each such expression compiles
to one correlated subquery on the related table, with the correct grain by
construction. The same grammar covers a `template(...)` function that formats
values, on the main table, on a one-side relation or, as a string aggregate,
on a many-side relation.

The grammar is additive. Every expression it introduces is a compile error
today (`not_existing_column`), so no existing query changes behaviour. It is
delivered through a second compiler selected by an instance switch; with the
switch off nothing changes (section 8).

Section 9 records the options considered and the choice made for each.

## 2. Motivation

### 2.1 Two ways a query is written

1. **By a developer**, in Python. Aggregates over a many-side relation are
   written as a `formulaColumn` with a correlated `select`:

   ```python
   tbl.formulaColumn('costi_pianificati_alla_data',
       select=dict(table='erpy_coge.piano_costi', columns='SUM($totale)',
                   where='$commessa_id=#THIS.id AND $data_decorrenza<=:data_selezionata'),
       dtype='N',
       ask=dict(title='Costi pianificati alla data',
                fields=[dict(name='data_selezionata', dtype='D', lbl='Data')]))
   ```

   The SQL is right. The cost is one declaration per (relation, column,
   function) in the model, plus `ask` for user parameters.

2. **By a user**, dragging leaves of the fields tree into a grid. The tree
   (`relationExplorer`, `gnrsqltable/utils.py`) forbids dragging a
   many-relation node itself (dtype `RM`, `genro_dev.js` `onDrag`), but allows
   any leaf below it, e.g. `@invoices.total`. The compiler then emits a LEFT
   JOIN on the many side, the rows multiply, `DISTINCT` is injected and the
   column is recorded in `explodingColumns`. `SqlSelection._aggregateRows`
   regroups the rows in Python and aggregates each exploding column by
   dtype (`fieldAggregate`).

### 2.2 What goes wrong today

Issue #1354 documents the failures of the second path, verified on
`test_invoice` (customer with 13 invoices and 43 invoice rows; true values
SUM(total) = 459362.22, SUM(quantity) = 1097):

| # | failure | effect |
|---|---|---|
| 1 | Python-level dedup in `_aggregateRows` | two invoices with equal total are summed once |
| 2 | injected `DISTINCT` fuses identical exploded rows | 42 rows fetched instead of 43; quantity 1058 instead of 1097 |
| 3 | `@invoices.total AS alias` is not aggregated | first value kept: 60111.97 instead of 459362.22 |
| 4 | dtype lost on the second hop | quantity aggregated as text `'1,3,4,5,...'` |
| 5 | different grain in one flat result | `SUM(@invoices.total)` with `@invoices.@rows.quantity` gives 1750128.54 |
| 6 | `view_store_aggregateRows=False` is read by nothing | dead parameter |

Failure 5 is structural: no function applied to the flat join can return
both SUM(total) and SUM(quantity) when two many-side relations are joined.
The aggregate must be computed per relation.

### 2.3 What already exists and is reused

| mechanism | where | what it gives |
|---|---|---|
| `formulaColumn(select=dict(table, columns, where))` | `compiler.py` getFieldAlias, select branch | compiles a correlated subquery with `db.queryCompile`, own alias prefix, `#THIS.<col>` bound to the outer row |
| `ask` + `formulaVariant` | `genro_grid.js` addColumn, `get_selection.py` formulaVariants, `table.py` getVirtualColumn | user fills parameters at drop time; the virtual column is cloned at query time with `var_*` overrides |
| `variant=` + `variantColumn_<name>` | `table.py` `_handle_variant_columns`, `columns.py`, `hierarchical.py` | derived virtual columns named `<field>_<suffix>` generated at model build |
| `relationExplorer` | `utils.py` | the tree; relations marked `RO`/`RM`; groups from the `group` attribute |
| `fieldAggregate` | `serialization.py` | the dtype → aggregator map (numeric SUM/MAX/MIN/AVG/CNT, boolean AND/OR, text join) |

All of them extend the *name* of a column to describe a transformation
(`field_unaccent`, `field_captions`, `field_hlv`, `costi_$curr_anno`). None of
them lets the *path* carry the transformation. This GEP does.

## 3. Current path grammar (verified)

| syntax | meaning | implemented in |
|---|---|---|
| `$col` | column of the main table | `COLFINDER` |
| `@rel.col`, `@rel.@rel2.col` | column through one or more relations; many-side hops explode | `getFieldAlias`, `_getRelationAlias` |
| `*`, `*prefix_` | all columns / columns by prefix | `expandMultipleColumns` |
| `*@rel`, `*@rel.prefix_` | all columns of a related table | `expandMultipleColumns` (#623 proposes deprecation) |
| `*@rel.(a,b,c)` | explicit list; fills `aggregateDict` (pivot keyed by `a`) | `expandMultipleColumns`; zero usages found, no tests |
| `#THIS.col` | outer row column inside a subquery | `THISFINDER` |
| `#IN_RANGE`, `#PERIOD`, `#TSQUERY`, ... | macros | macro expander |
| `SUM(@rel.col)` | SQL text passed through; wrong grain beyond one hop | textual |

Tokens are recognised by `COLRELFINDER = ([@$]\w+(?:\.\w+)*)`: a
parenthesis ends the token. This is why `@invoices.sum($total)` is currently
read as `@invoices.sum` (unknown column) followed by `(total)`.

## 4. Proposal — core grammar

### 4.0 Rule

A many-side relation in a path always requires an aggregating function with
explicit arguments (decided 2026-09-20). `sum`, `count`, `avg`, `min`, `max`
are aggregating functions; so are `to_array` and `to_json` (9.6). What is
aggregated and how must be readable from the expression alone. The legacy
form `@rows.quantity` (bare leaf under a many-side relation, exploding join
plus `_aggregateRows`) is not part of this grammar; it keeps working as today
until it is removed by a later change.

### 4.1 Form

```
<relpath> '.' <function> '(' [ <args> ] ')'
```

- `<relpath>` is an existing relation path, `@rel` or `@rel.@rel2...`, whose
  last hop is a many-side relation (`joiner.mode == 'M'` and not `one_one`).
- `<function>` is one of `count`, `sum`, `avg`, `min`, `max` (core set).
- `<args>` is a column of the related table, optionally wrapped in the
  modifier `distinct(col)`. `count()` takes no argument.

### 4.2 Semantics

The expression is **one value per row of the outer table**, computed over
the set of rows reached by `<relpath>` from that row. It compiles to a
correlated subquery whose FROM is the last table of the path and whose WHERE
walks the path back to `#THIS.<pkey>`.

Verified on `test_invoice` (the SQL below is what the select branch of the
compiler produces today for an equivalent `formulaColumn`):

| expression | compiled subquery | result |
|---|---|---|
| `@invoices.count()` | `SELECT COUNT(*) FROM invc_invoice t WHERE t.customer_id = t0.id` | 13 |
| `@invoices.sum($total)` | `SELECT SUM(t.total) FROM invc_invoice t WHERE t.customer_id = t0.id` | 459362.22 |
| `@invoices.@rows.count()` | `SELECT COUNT(*) FROM invc_invoice_row r JOIN invc_invoice i ON r.invoice_id = i.id WHERE i.customer_id = t0.id` | 43 |
| `@invoices.@rows.sum($quantity)` | same FROM, `SUM(r.quantity)` | 1097 |
| `@invoices.@rows.count(distinct($product_id))` | same FROM, `COUNT(DISTINCT r.product_id)` | 43 |

No `DISTINCT` on the outer query, nothing in `explodingColumns`, no Python
post-processing. Several expressions on different relations coexist in one
SELECT with the right grain each.

### 4.3 Multi-hop

`@invoices.@rows.sum($quantity)` aggregates over **all** rows reachable
through the whole path (all invoice rows of all invoices of the customer),
with an inner join per intermediate hop. This is the only reading the core
grammar gives to a path.

Nested aggregates, one per hop, express a different quantity:
`@invoices.avg(@rows.sum($quantity))` = average over the invoices of the
per-invoice sum. The argument of the outer function is itself a relation
function, evaluated per row of the outer relation. Verified on `test_invoice`
by nesting two `select` formula columns (the compiler already produces it):

```sql
SELECT AVG((SELECT SUM(r.quantity) FROM invc_invoice_row r WHERE r.invoice_id = i.id))
FROM invc_invoice i WHERE i.customer_id = t0.id        -- 84.38 = 1097 / 13
```

against `@invoices.@rows.avg($quantity)` = 1097 / 43 = 25.51 (average over the
rows). Whether the argument grammar admits a nested relation function is
option 9.3.

### 4.4 Where, order by, group by

The expression is a column like any other and can appear wherever a column
can:

```
where='@invoices.sum($total) > :threshold'
order_by='@invoices.count() DESC'
```

In `where` it becomes a subquery in the WHERE clause; the compiler needs no
DISTINCT and no join. Note for the implementation: `GnrWhereTranslator.innerFromBag`
calls `tblobj.column(column)` before translating a query-bag row, so the
query editor path needs the same resolution as the compiler.

### 4.5 Output name — DECIDED: human-readable, truncation rule later (2026-09-20)

Without `AS`, the compiler derives the output name from the structure of the
expression, in the convention of today's `_invoices_total`: relation path,
function, argument names; separators and other extra arguments are left out.

| expression | output name |
|---|---|
| `@invoices.count()` | `_invoices_count` |
| `@invoices.sum($total)` | `_invoices_sum_total` |
| `@invoices.@rows.count(distinct($product_id))` | `_invoices_rows_count_distinct_product_id` |
| `@invoices.avg(@rows.sum($quantity))` | `_invoices_avg_rows_sum_quantity` |

The mechanical `colToAs` (`\W` → `_`) is not used: it would give
`_invoices_sum__total_`.

- Names longer than the identifier limit (63 characters on PostgreSQL): a
  truncation rule, to be defined later. Positional names (`_agg1`, `t3_count`)
  are rejected as the main rule because they change with the order of the
  columns and joins.
- `template(...)` and any expression containing a free string: `AS` is
  mandatory, explicit error otherwise.
- The fields tree emits `fieldname` next to `fieldpath` on each aggregate
  leaf, so the grid cell name is decided once, server side, and the client
  does no parsing of the path (it already uses `fieldname` in the
  `formulaVariant` flow).

## 5. Proposal — `template(...)`

`template` is a **row-level** function: it formats one row with a `$name`
template (the convention of `gnrstring.templateReplace`, already used by the
compiler). It replaces the `formulaColumn` written today with the `||`
operator. With decision 9.2 the placeholders are the fields themselves, so
no argument list follows the template string.

| level | example | SQL |
|---|---|---|
| main table | `template('$name ($code)')` | `t0.name || ' (' || t0.code || ')'` |
| one-side relation | `@customer_id.template('$name ($code)')` | same, on the joined one-side row |
| inside an aggregate argument | `@invoices.max(template('$year-$number'))` | formatted per related row, then aggregated |

Optional named arguments add `#name` placeholders next to the `$field`
ones (decided 2026-09-20):

```
template('<string>' [, <expression> AS <name>, ...])
template('total #ttl over #n invoices', @invoices.sum($total) AS ttl, @invoices.count() AS n)
```

`$x` is always a field of the current row; `#x` is always a named argument.
This is the convention the compiler already uses for named subselects in the
`select` branch (`#default`, `#captions`). Argument names must not coincide
with macro names (`#THIS`, `#PERIOD`, `#IN_RANGE`, ...), which are expanded
first. Each expression follows the general field grammar (decision 9.2), so
relation functions are allowed. Non-text values are CAST
to text before concatenation (`||` on a number fails on PostgreSQL).

On a many-side relation `template` alone is an error: one string per related
row cannot become one value without an aggregate. Text aggregation over a
many-side relation (`string_agg` / `group_concat`, separator, order) is a
separate function, not part of this GEP; see 9.4.

Prior art: `variantColumn_captions` (`columns.py`) builds such a string with
`array_to_string(ARRAY(select ...), sep)`; `fieldAggregate` joins unique text
values with `','`.

## 6. Proposal — declaring aggregable columns in the model

A column declares that it is aggregable with the `aggregate` parameter
(decided 2026-09-20). Its value depends on the dtype:

| dtype | `aggregate=True` | other values |
|---|---|---|
| numeric (`N`, `L`, `R`, `I`) | `sum` | comma-separated list of functions: `aggregate='sum,avg,min,max'` |
| text (`A`, `T`) | text aggregate with separator `','` | the value is the separator: `aggregate='/'` |
| date, datetime, boolean | treated as text: CAST to text, then text aggregate with `','` | the separator, as for text; an explicit list (`aggregate='min,max'` on a date) uses the native SQL functions |

```python
tbl.column('quantity', dtype='L', aggregate='sum,avg,min,max')
tbl.column('total', dtype='N', aggregate=True)          # sum
tbl.column('number', dtype='A', aggregate=' / ')        # 'A-1 / A-2 / A-3'
```

Effects:

- `relationExplorer`, when expanding a many-relation node (`RM`), adds a
  group `aggregated` with one leaf per function: `@rows.sum($quantity)`,
  `@rows.avg($quantity)`, ... with the dtype of the column (`L` for `count`).
  `count()` is a leaf of the relation itself, always present, not declared.
- Leaves have a dtype, so the fields tree lets the user drag them without any
  client change. The drop produces a path the compiler understands: no
  explosion, no `_aggregateRows`.
- The parameter is **opt-in**. Without it the tree does not grow
  (columns × functions × hops).

Two places, both valid (decided 2026-09-20):

1. **On the column** (above): the column is aggregable under every many-side
   relation that reaches its table.
2. **On the relation**, as a chained call on the relation node returned by
   `relation()`, to restrict or extend the leaves of that node only:

   ```python
   tbl.column('invoice_id', size='22').relation('invoice.id', relation_name='rows'
              ).aggregations('quantity:sum,avg', 'unit_price:sum')
   ```

   The relation setting overrides the column setting for that node. It is
   stored as an attribute of the relation node, which `relationExplorer`
   already merges into the `RM` node through the `joiner` attributes.

For a text column the tree emits `@invoices.sum($number)`: `sum` on text is
the text aggregate (decision 9.4) and the declared separator is its default.

The existing `aggregator` attribute (read by `fieldAggregate`, one use in the
framework: `__is_invalid` with `OR`) selects the Python aggregator for the
old path. It is left untouched by this GEP.

Out of scope: trees saved in `adm.tblinfo_item` (`gnrwebpage.py`
`relationExplorer` with `item_type`). They are served as stored and do not
gain the new leaves unless regenerated. Declared limit, not addressed here.

## 7. Dialects

| function | PostgreSQL | SQLite | note |
|---|---|---|---|
| count, sum, avg, min, max | standard | standard | no adapter code |
| count(distinct(x)) | `COUNT(DISTINCT x)` | same | modifier, not a function |
| template (row level) | `||` concatenation | `||` concatenation | no adapter code |
| sum on text (9.4) | `string_agg(expr, sep ORDER BY ...)` | `group_concat(expr, sep)` (order not guaranteed) | adapter |
| boolean and/or | `bool_and`, `bool_or` | `MIN`, `MAX` on 0/1 | adapter, if added |
| to_array, to_json (9.6) | `json_agg`, `json_build_object` | `json_group_array`, `json_object` | adapter |

## 8. Transition plan

The grammar is delivered through a second compiler, never by editing the
current one (decided 2026-09-20).

### 8.1 Two compilers behind one factory

`SqlQueryCompiler` is constructed in two places (`gnrsqldata/query.py`
`compileQuery`, `gnrsqldata/record.py`). A factory at those two points picks
the compiler:

| switch (instance config) | compiler |
|---|---|
| off | current `SqlQueryCompiler`, byte-for-byte the same SQL as today |
| on | new compiler, a copy of the current one that receives all pending work |

The current compiler is frozen: no pending PR touches it any more. The new
compiler absorbs #1352 (macro registry), #1353 (RuntimeModel), this GEP and
the later reports from the `sql_review/*` branches. Until new syntax is
used, the two compilers must produce identical SQL: a reference corpus of
compiled queries on `test_invoice` is the acceptance test of the switch.

### 8.2 Alternative app handler on a table proxy

`page.app` (`gnrwebpage.py`) instantiates `GnrWebAppHandler`. The same switch
selects an alternative handler that delegates the table-level work
(columns from struct and from string, where-bag decoding, default query
construction, saved views and queries, aggregate leaves of the fields tree)
to a new **table proxy in the app layer** (`gnr.app`, next to
`hierarchicalHandler` and `xtd`). The page keeps only what belongs to the
page: permissions, locale, frozen selections, page store, page hooks
(`selectmethod`, `applymethod`), client publishing and the shape of the RPC
result. Pure refactoring: same results, verified by a comparison suite run
through both handlers on `db_sqlite` and `db_pg`. Batch jobs, prints and
plain Python code gain a way to build the same queries without a page.

### 8.3 `_aggregateRows` in the new path

In the new handler `_aggregateRows` is no longer passed by default. An
explicit `_aggregateRows=True` together with new syntax is ignored with a
warning: the new compiler produces no exploding columns, so there is
nothing to re-aggregate. The legacy path is untouched.

### 8.4 Order of work

| step | depends on |
|---|---|
| reference corpus of compiled SQL | — |
| alternative app handler + table proxy + switch + comparison suite | — |
| compiler factory + new compiler (copy) + switch + comparison suite | — |
| `manyRelation` in the model (separate PR; condition handled by the legacy compiler only if low risk, otherwise by the new one only) | — |
| `aggregate=` on columns, `.aggregations()` on relations (attributes only) | — |
| retarget #1352 and #1353 onto the new compiler | factory |
| this grammar in the new compiler, one resolver for every consumer (9.8) | factory, retarget |
| aggregate leaves in the tree, `fieldname` from the server | handler, attributes, grammar |
| removal of `*@rel.(a,b)` (#623); later deprecation of `_aggregateRows` and of the legacy compiler | grammar in use |

The first five rows are independent and can proceed in parallel from
`develop`.

## 9. Options to decide

### 9.1 Surface syntax — DECIDED: A (2026-09-20)

| option | example | pros | cons |
|---|---|---|---|
| **A. method on the relation** (proposed) | `@invoices.sum($total)` | says *which relation* aggregates; reads like a method; args are plain column names | new token shape (parenthesis inside a path) |
| B. SQL function outside | `SUM(@invoices.total)` | already accepted textually | ambiguous relation on two hops; wrong grain today |
| C. suffix (variant style) | `@invoices.total_sum` | no parser change beyond a name lookup | no arguments (`distinct`, template); collides with real column names |
| D. colon modifier | `@invoices.total:sum` | short | `:` is the bind-parameter prefix in SQL text |

### 9.2 Argument style — DECIDED: B (2026-09-20)

Arguments use the general field grammar of the related table: `$col` for a
column, `@rel...` for a path, so `@invoices.sum($total)`,
`@rows.count(distinct($product_id))`, `@invoices.avg(@rows.sum($quantity))`.
Reason: since arguments may be paths, the notation must be the one used
everywhere else. Consequence: the argument is a formula fragment evaluated on
the related table, so `@rows.sum($quantity * $unit_price)` follows without
extra rules. Option C (relation name in place of the FK column) is rejected.


| option | example | note |
|---|---|---|
| **A. bare column names** (proposed) | `sum(total)`, `count(distinct(product_id))` | columns of the related table, no `$` |
| B. `$`-prefixed | `sum($total)` | consistent with formulas; `$` inside a path token |
| C. relation names allowed for FK | `count(distinct(product))` | resolve `@product_id` → `product_id`; convenience, one more rule |

### 9.3 Multi-hop semantics — DECIDED: A and B, both in core (2026-09-20)

The argument shape tells them apart (`$col` vs `@path`), so no extra rule.

| option | `@invoices.@rows.sum($quantity)` means | note |
|---|---|---|
| **A. flat set** (proposed) | sum over all rows reachable | one subquery with inner joins |
| B. nested, explicit | `@invoices.avg(@rows.sum($quantity))` | subquery in subquery, verified (section 4.3); A and B coexist because the argument shape differs (column vs relation function); B needs the argument grammar to accept a path |

### 9.4 Text aggregation on many side — DECIDED: `sum` overloaded by dtype (2026-09-20)

No new function name. `sum` on a text argument is the text aggregate, with an
optional second argument as separator:

```
@invoices.sum($number)          -- separator from the model (aggregate='/'), else ','
@invoices.sum($number, ' | ')   -- explicit separator
@invoices.sum(template('#y-$number', $year AS y))   -- formatted rows, then joined
```

The compiler knows the dtype of the argument (column attribute, or text for
`template`), so it maps `sum` to `string_agg` (PostgreSQL) or `group_concat`
(SQLite) in the adapter. `concat` was considered as an alias and not adopted.
Row order inside the string: the `order_by` attribute of the related table,
else its pkey (`string_agg(... ORDER BY ...)`; SQLite does not guarantee it).

### 9.5 Model parameter — DECIDED: `aggregate=` on the column (2026-09-20)

Semantics by dtype as in section 6. Date, datetime and boolean columns with
`aggregate=True` are treated as text (decided 2026-09-20): a standard ISO
CAST (`YYYY-MM-DD`, `YYYY-MM-DD HH:MM:SS`, the same on PostgreSQL and SQLite),
then joined. No format parameter in this GEP: a different rendering is
obtained by declaring a string `variant` on the column and aggregating that.
Improving variants for this purpose is the subject of a separate GEP. Declared on the column and, per relation node, with
`.aggregations(...)` chained on `relation()`; the relation overrides the
column (section 6).

### 9.6 Fate of `*@rel.(a,b)` — DECIDED: deprecate and remove (2026-09-20)

The form does not say what it aggregates nor how (the first argument is
silently the key: `compiler.py:810`). It is removed with #623, together with
the `aggregateDict` branch of `_aggregateRows`.

Structured aggregates are ordinary aggregating functions of the grammar,
with explicit meaning (names tentative, to confirm):

| function | example | result | SQL |
|---|---|---|---|
| `to_array` | `@rows.to_array($quantity)` | JSON array of the values: `[3, 12, ...]` | `json_agg(x)` / `json_group_array(x)` |
| `to_json` | `@rows.to_json($product_id, $quantity)` | JSON array of objects: `[{"product_id": "P001", "quantity": 3}, ...]` | `json_agg(json_build_object(...))` / `json_group_array(json_object(...))` |

Result dtype `X` (delivered as a Bag). A keyed object is not provided; it can
be added later as its own function with the key named explicitly.

### 9.7 Filtering the aggregated set — DECIDED: no filter syntax (2026-09-20)

No bracket filter and no `where=` argument. A filtered subset is a relation
of its own in the model (`@invoices_prev.sum($total)`), declared on the
one-side table with `manyRelation(name, '@relation', condition=...)`. That
declaration is an ordinary change, delivered as its own PR, not part of this
GEP. Query-time filters stay with the existing `joinConditions` /
`setJoinCondition` mechanism.

### 9.8 Where does the grammar live — DECIDED: everywhere (2026-09-20)

A relation function must be usable in every place a field can appear:
`columns`, `where` (hand-written and from the query editor), `order_by`,
`group_by`, `having`, `sql_formula` of a formula column, conditions of
relations. This rules out adding the syntax to one consumer at a time.

Consequence for the compiler: field expressions are parsed today by
independent regex passes (`COLFINDER`, `RELFINDER`, `COLRELFINDER` in
`compiler.py:62-64`, applied in `updateFieldDict` and the column/where/order
handling of `compiledQuery`) and, separately, by `GnrWhereTranslator.innerFromBag`
(`tblobj.column(column)` before translating a query-bag row). Making the
grammar available everywhere means one resolver for field expressions, used
by all of them. Whether this is an extension of `getFieldAlias` or a redesign
of the compiler's parsing layer is assessed in the branch; the GEP records
the requirement, not the implementation.

## 10. Consequences

- New views built by users from the fields tree stop producing exploding
  columns for aggregable fields. `_aggregateRows` stays for existing queries
  and becomes progressively unused. This GEP does not change it.
- Many `formulaColumn(select=...)` declarations that exist only to expose an
  aggregate become one word in a view. `formulaColumn` stays for
  parametrised or filtered aggregates.
- The fields tree gains a stable place (`aggregated` group) for aggregates,
  discoverable by users.

## 11. Appendix — verification data

`test_invoice`, SQLite, customer `wmD1WDP7Ntqo2Dlqja1iQQ` (Zoe Lee):

```
invoices                    13
SUM(invoice.total)          459362.22
invoice rows                43
SUM(invoice_row.quantity)   1097
distinct products in rows   43
```

Flat join with two many-side relations, hand-written aggregates,
`group_by='$account_name'`:

```
SUM(@invoices.total)            1750128.54   (wrong: multiplied by rows)
SUM(@invoices.@rows.quantity)   1097         (right)
SUM(DISTINCT @invoices.total)   459362.22    (right only while all totals differ)
```

Correlated subqueries (one per relation), same data: all values right, see
section 4.2.
