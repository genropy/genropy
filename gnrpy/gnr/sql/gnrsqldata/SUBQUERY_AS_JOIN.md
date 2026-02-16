# Subquery-as-Join: Converting Correlated Subqueries to LEFT JOINs

## Overview

Genro's `formulaColumn` mechanism allows tables to declare virtual columns whose
values are computed by a correlated subquery.  For example, a `customer` table
can declare a `n_invoices` formula that counts how many invoices belong to each
customer.

Traditionally, the SQL compiler embeds each formula as an **inline correlated
subquery** inside the SELECT clause.  The database re-executes the subquery once
per row in the result set.  This works correctly in all cases, but on large data
sets with multiple formula columns the performance impact can be significant.

The *subquery-as-join* feature provides an alternative compilation strategy: it
rewrites eligible formula columns as **LEFT JOINs** on pre-aggregated subqueries.
The database executes each subquery once (not once per row), producing a
dramatic speed-up on large tables.

The conversion is fully **opt-in** and **backward-compatible**: when disabled,
the compiler behaves exactly as before.


## How the enable flag works

The conversion is controlled at three independent levels.  If **any** of the
three is active for a given column in a given query, the conversion takes place.

### Level 1 — Per-column

When declaring the formula in the model, the developer can force that specific
column to always be compiled as a join:

```python
tbl.formulaColumn('n_invoices',
                  select=dict(table='pkg.invoice',
                              columns='COUNT(*)',
                              where='$customer_id=#THIS.id'),
                  sq_as_join=True,    # <-- always convert this column
                  dtype='L')
```

This is useful when the developer knows in advance that a particular formula
will always run against large tables.

### Level 2 — Per-query

The caller can request conversion for all eligible formulas in a single query:

```python
db.query('pkg.customer',
         columns='$name, $n_invoices, $invoiced_total',
         enable_sq_join=True)    # <-- convert all formulas in this query
```

This is useful in application code where the developer knows the specific query
will touch many rows and wants the join optimization.

### Level 3 — Global

The conversion can be enabled as the default behavior for the entire database:

```python
db.extra_kw['subquery_as_join'] = True    # <-- all queries, all tables
```

This is a deployment-level setting.  Applications can turn it on globally after
validating that their formulas produce correct results with the join strategy.


## What happens when the compiler encounters a formulaColumn

When the SQL compiler processes a column and discovers that it is a
formulaColumn backed by a `select` dictionary (a subquery definition), the
following decision tree executes:

1. **Check the enable flag**.  The compiler inspects the three levels described
   above.  If none of them is active, the formula is compiled as a traditional
   inline correlated subquery, and the process ends here.

2. **Check for circular references**.  The compiler scans the formula's WHERE
   clause looking for `#THIS.xxx` references where `xxx` is itself a
   formulaColumn with a subquery on the same table.  If such a reference is
   found, the conversion is **skipped** and the formula stays inline.  This
   safety check is described in detail in a later section.

3. **Register the subquery for processing**.  The formula's definition (table,
   columns, where, group_by, order_by, limit) is stored in a preprocessing
   dictionary, keyed by column name.

4. **Compile and attach**.  After all columns have been processed, the compiler
   runs the condensation pass (described below), compiles each independent
   subquery, and appends the resulting LEFT JOINs to the main query.


## The safety check: formulas referencing other formulas

Some formula columns depend on the result of another formula column.  Consider
this example on the `customer` table:

- `top_product_id`: a formula that finds the product with the highest total
  sales for this customer (uses GROUP BY, ORDER BY, LIMIT 1).
- `top_product_n_sold`: a formula that counts how many units of the top product
  were sold to this customer.  Its WHERE clause contains
  `$product_id = #THIS.top_product_id`.

The second formula references `#THIS.top_product_id`, which is itself a formula
column.  In the inline strategy this works because the database evaluates each
correlated subquery independently for each row: it first computes
`top_product_id` as an inline scalar, then uses that value in the WHERE of
`top_product_n_sold`.

If both formulas were converted to LEFT JOINs, there would be a problem: the
second join would need to reference the **result** of the first join, but the
SQL engine does not guarantee evaluation order between joins.  The result could
be incorrect or cause a SQL error.

The compiler prevents this by inspecting the WHERE clause of each candidate
formula before conversion.  It extracts every `#THIS.xxx` reference and checks
whether `xxx` is defined as a formulaColumn with a subquery in the same table.
If it is, the candidate formula is **excluded from conversion** and remains
inline.

This is a conservative strategy: it may leave some formulas inline that could
theoretically be converted (if the dependency were resolved in a specific
order), but it guarantees correctness.  The guiding principle is that
**correctness always takes precedence over performance**.  A slower query that
returns the right answer is always preferable to a faster query that returns
wrong numbers.

### In practice

For the `customer` table with the formulas described above, when the conversion
is active:

| Formula              | Strategy   | Reason                                      |
|----------------------|------------|---------------------------------------------|
| `n_invoices`         | LEFT JOIN  | No formula dependencies                      |
| `invoiced_total`     | LEFT JOIN  | No formula dependencies                      |
| `last_invoice_date`  | LEFT JOIN  | No formula dependencies                      |
| `avg_invoice_total`  | LEFT JOIN  | No formula dependencies                      |
| `max_invoice`        | LEFT JOIN  | No formula dependencies                      |
| `min_invoice`        | LEFT JOIN  | No formula dependencies                      |
| `top_product_id`     | LEFT JOIN  | No formula dependencies                      |
| `top_product_n_sold` | **INLINE** | WHERE references `#THIS.top_product_id`      |
| `last_invoice_id`    | LEFT JOIN  | No formula dependencies                      |


## Preprocessing: extracting the join condition

When a formula column is eligible for conversion, the compiler needs to
separate its WHERE clause into two parts:

1. **The join condition**: the part that links the subquery table to the main
   table.  For example, `$customer_id = #THIS.id` means "the customer_id column
   in the subquery table must match the id of the current row in the main
   table."  This condition becomes the ON clause of the LEFT JOIN.

2. **The residual filter**: any additional conditions that restrict the subquery
   but do not reference the main table.  For example, in a formula that counts
   invoices for a specific year, the WHERE might be
   `$customer_id = #THIS.id AND EXTRACT(YEAR FROM $date) = 2024`.  The first
   part is the join condition; the second part is a filter that stays inside
   the subquery.

The compiler parses the WHERE clause, identifies the `#THIS` references, and
splits accordingly.  The join condition will be used to connect the subquery
to the main query via the ON clause, while the residual filter remains as a
WHERE inside the subquery itself.


## Condensation: merging subqueries with the same identity

This is the most important optimization in the entire mechanism.

Consider a `customer` table with four formula columns, all pointing to the
`invoice` table with the same join condition (`$customer_id = #THIS.id`):

- `n_invoices` = `COUNT(*)`
- `invoiced_total` = `SUM($total)`
- `last_invoice_date` = `MAX($date)`
- `avg_invoice_total` = `AVG($total)`

Without condensation, the compiler would create four separate LEFT JOINs, each
with its own subquery.  All four subqueries scan the same table with the same
join condition — the only difference is the aggregate function.

Condensation detects this situation and merges the four subqueries into a
**single LEFT JOIN** that computes all four aggregates at once:

```sql
LEFT JOIN (
    SELECT customer_id,
           COUNT(*)    AS n_invoices,
           SUM(total)  AS invoiced_total,
           MAX(date)   AS last_invoice_date,
           AVG(total)  AS avg_invoice_total
    FROM invoice
    GROUP BY customer_id
) AS sq0 ON sq0.customer_id = t0.id
```

### How the identity hash works

To determine which subqueries can be merged, the compiler computes an
**identity hash** for each one.  The hash combines:

- The **target table** (fully qualified name).
- The **join condition** (the part of the WHERE that references `#THIS`).

If two formula columns produce the same identity hash, they reference the same
"slice" of data and can be served by a single subquery with multiple aggregate
columns.

### Condensation with different filters

Formula columns that share the same target table and join condition but have
**different residual filters** produce different identity hashes and are compiled
into separate LEFT JOINs.

For example, on the `customer` table:

- `invoiced_2024` = `SUM($total)` WHERE `$customer_id=#THIS.id AND EXTRACT(YEAR FROM $date)=2024`
- `invoiced_2025` = `SUM($total)` WHERE `$customer_id=#THIS.id AND EXTRACT(YEAR FROM $date)=2025`
- `n_invoices_2024` = `COUNT(*)` WHERE `$customer_id=#THIS.id AND EXTRACT(YEAR FROM $date)=2024`

Here, `invoiced_2024` and `n_invoices_2024` share the same identity hash (same
table, same full WHERE including the year filter), so they are condensed into
one LEFT JOIN.  `invoiced_2025` has a different hash (different year filter) and
becomes a separate LEFT JOIN.

The result is an optimal number of joins: one per distinct (table, full-where)
combination, each carrying as many aggregate columns as needed.


## The special case: LIMIT 1 subqueries

Some formula columns do not compute a simple aggregate.  Instead, they find a
**specific value** from an ordered and grouped result set.  For example:

- "The product with the highest total sales for this customer" — requires
  grouping invoice rows by product, ordering by total descending, and taking
  only the first row.

These formulas have `group_by`, `order_by`, and `limit=1` in their definition.
They cannot be converted to a simple LEFT JOIN with GROUP BY, because the
result is not a single aggregate per group but a specific row from a ranked
set.

The compiler handles these formulas differently.  Instead of a GROUP BY
subquery, it generates a subquery that uses the **ROW_NUMBER()** window
function:

```sql
LEFT JOIN (
    SELECT customer_id,
           product_id,
           ROW_NUMBER() OVER (
               PARTITION BY customer_id
               ORDER BY SUM(tot_price) DESC, product_id
           ) AS rn
    FROM invoice_row
    GROUP BY customer_id, product_id
) AS sq1 ON sq1.customer_id = t0.id AND sq1.rn = 1
```

The ROW_NUMBER() is partitioned by the join field (customer_id), so each
customer gets its own ranking.  The ON clause includes `rn = 1` to select
only the top-ranked row for each customer.

### Condensation of LIMIT 1 subqueries

LIMIT 1 subqueries also participate in condensation.  If two formula columns
both look for a "top something" from the same table with the same WHERE
(for example, `top_customer_id` and `top_state` both querying `invoice_row`
WHERE `$product_id = #THIS.id`), they are merged into a single LEFT JOIN
that returns both columns:

```sql
LEFT JOIN (
    SELECT product_id,
           customer_id    AS top_customer_id,
           customer_state AS top_state,
           ROW_NUMBER() OVER (
               PARTITION BY product_id
               ORDER BY SUM(tot_price) DESC
           ) AS rn
    FROM invoice_row
    JOIN invoice ON ...
    JOIN customer ON ...
    GROUP BY product_id, customer_id, customer_state
) AS sq2 ON sq2.product_id = t0.id AND sq2.rn = 1
```


## Independent compilation with manglers

Each subquery that becomes a LEFT JOIN is compiled as an **independent query**
with its own compiler instance.  This is necessary because the subquery may
traverse different relations than the main query.  For example, a formula
column on the `product` table might navigate through `invoice_row` to
`invoice` to `customer` to get the customer's state — a chain of relations
that the main product query does not use.

The independent compiler receives its own **mangler**: a unique prefix (such as
`sq0`, `sq1`, `sq2`) that is prepended to all table aliases generated inside
the subquery.  This prevents naming conflicts: if the main query uses alias
`t0` for the customer table and the subquery also needs the customer table,
the subquery will use `sq0_t0` instead.

The mangler is generated by the main query's `_next_mangler_key()` method,
which maintains a counter to ensure uniqueness.  The prefix `sq` (for
"subquery") distinguishes these manglers from `cq` manglers used by the
compound query feature (UNION/INTERSECT/EXCEPT).

The independently compiled subquery produces a complete SQL fragment: SELECT
with aggregate columns, FROM with any internal joins needed to traverse
relations, WHERE with residual filters, and GROUP BY.  This fragment is
wrapped in parentheses and attached to the main query as a LEFT JOIN with
the appropriate ON clause.


## Expansion of placeholders

Formula column definitions use special placeholders that are resolved at
compile time.

### #THIS — Current row reference

The most important placeholder.  `#THIS.id` means "the id column of the
current row in the main table."  When the compiler processes a formula's
WHERE clause, it replaces `#THIS.xxx` with the actual SQL reference to
column `xxx` in the main query.  For example, if the main table has alias
`t0`, then `#THIS.id` becomes `t0.id`.

In the context of subquery-as-join, the `#THIS` reference in the join
condition becomes the right side of the ON clause.  In a residual filter,
it is expanded using the main query's alias system.

### #ENV — Environment variables

`#ENV.xxx` references the current application environment.  For example,
`#ENV.user` might expand to the currently logged-in user.  The compiler
looks up the value in the database's `currentEnv` dictionary and substitutes
a literal string.  If the value is not found, it tries to call an
`env_xxx` method on the table model object.

### #PREF — Package preferences

`#PREF.xxx` references a configuration preference from the table's package.
For example, `#PREF.default_currency` might expand to `'EUR'`.  The
compiler reads the preference value via the table model's package and
substitutes a literal string.

### Historical note

In the previous monolithic implementation, the expansion functions
(`expandThis`, `expandPref`, `expandEnv`) were local closures defined inside
the `getFieldAlias` method.  They captured the current table, alias, and
table object from the enclosing scope.

In the split module architecture, these functions have been promoted to
methods of the `SqlQueryCompiler` class.  The compiler saves the current
context (`_curr`, `_alias`, `_curr_tblobj`) as instance attributes during
field processing, so the expansion methods can access them via `self`.
This refactoring was necessary to allow the expansion logic to be invoked
during independent subquery compilation.


## The complete compilation flow

Here is what happens, step by step, when a query with `enable_sq_join=True`
is compiled:

1. The compiler iterates over the requested columns, resolving each one
   against the table model.

2. For each column that is a formulaColumn backed by a `select` dictionary:
   - The compiler checks the three-level enable flag.
   - If enabled, it checks for circular formula references.
   - If safe, it calls `_handleFormulaColumn`, which registers the
     subquery definition in the `sq_compiled_dct` preprocessing dictionary
     and returns a placeholder column reference (pointing to the future
     LEFT JOIN alias).
   - If not safe (circular reference) or not enabled, it compiles the
     formula as a traditional inline subquery.

3. After all columns are processed, the compiler runs `_preprocess_subqueryes`
   on the collected definitions.  This step parses each formula's WHERE
   clause, extracts the join condition, and normalizes the subquery
   parameters.

4. The compiler runs `_condense_subqueries`.  This step computes the
   identity hash for each subquery, groups subqueries with the same hash,
   and merges their aggregate columns into a single subquery definition.

5. For each condensed subquery group, the compiler calls `_compiledSubQuery`,
   which:
   - Creates a new `SqlQueryCompiler` instance with a fresh mangler.
   - Compiles the subquery independently, resolving all relations and
     expanding all placeholders.
   - For LIMIT 1 subqueries, wraps the result in a ROW_NUMBER() construct.
   - Produces a `SqlCompiledSubQuery` instance (a subclass of
     `SqlCompiledQuery` that carries the identity hash).

6. Each compiled subquery is converted to a LEFT JOIN SQL fragment and
   appended to the main query's join list.

7. The main query's column references for the formula columns are updated
   to point to the appropriate alias and column in the LEFT JOIN.

8. The final SQL text is generated with all the LEFT JOINs in place.


## The SqlCompiledSubQuery class

`SqlCompiledSubQuery` is a subclass of `SqlCompiledQuery` that adds one
attribute: the **identity hash**.  This hash is used during condensation to
identify which subqueries can be merged.

The class also overrides the SQL text generation to produce a subquery
suitable for use as a LEFT JOIN source (wrapped in parentheses, with an
alias).  The template wrapping mechanism (`self.tpl`) handles the
ROW_NUMBER() case by applying the window function wrapper when the formula
has `order_by` and `limit=1`.


## Test coverage

The feature is validated by 26 tests running against a PostgreSQL database
populated with realistic data (3,200 customers, 60,000 invoices, 410,000
invoice rows).

### test_subquery_join.py (14 tests)

Each test queries the same formula column twice — once with the default
inline strategy and once with `enable_sq_join=True` — and asserts that the
results are identical.

- **TestCustomerSubqueryJoin** (5 tests): `n_invoices`, `invoiced_total`,
  `last_invoice_date`, `avg_invoice_total`, and all four together.

- **TestProductSubqueryJoin** (2 tests): `n_sold`, `total_sold`.

- **TestInvoiceSubqueryJoin** (2 tests): `n_rows`, `row_total`.

- **TestProductTopSubqueryJoin** (3 tests): `top_customer_id`, `top_state`,
  and `top_customer_all` (full dataset, no limit).

- **TestSqlTextGeneration** (2 tests): verifies that the inline strategy
  produces nested SELECTs while the join strategy produces LEFT JOIN in the
  generated SQL text.

### test_subquery_where_orderby.py (12 tests)

Tests that formula columns work correctly in WHERE and ORDER BY clauses
with both strategies.

- **TestWhereOnFormulaColumn** (5 tests): filtering by `n_invoices > N`,
  `invoiced_total > N`, `n_sold = 0`, combined real column + formula column,
  `last_invoice_date > date`.

- **TestOrderByFormulaColumn** (5 tests): ordering by `n_invoices DESC`,
  `invoiced_total DESC`, `n_sold DESC`, `total_sold ASC`, `n_rows DESC`.

- **TestWhereAndOrderByCombined** (2 tests): simultaneous WHERE and ORDER BY
  on different formula columns, with limit.
