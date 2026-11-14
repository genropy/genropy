<!-- generated from counter-blocks.xml by xmldocs: do not edit, edit the XML -->

## adm.counter: numbers kept as blocks, opt-in per counter
*Proposal · counter-blocks · 2026-11-14 · draft*

### Problem

A recycling counter (`recycle=True`) keeps its free numbers in the `holes` Bag of the counter record. The Bag is a second copy of what the document table already says, and it drifts from it: genropy/genropy#1879 shows a release that took the counter back below numbers in use, and `alignSequences` is needed to rebuild the state from the documents.

The goal is a model of the numbers of a series that is easy to keep consistent, gives the free numbers and their allowed dates without extra searches, and keeps the current API: `counter_<field>()`, `assignCounterColumn`, `releaseCounterColumn`, `guessCounter`.

### Current state

#### How the counter works today

- `READ` `projects/gnrcore/packages/adm/model/counter.py:25` · 2026-11-14 — The free numbers of a series live in the `holes` column (dtype `X`) of its `adm.counter` record, one node per hole with `cnt_from`, `cnt_to`, `date_from`, `date_to`.
- `READ` `projects/gnrcore/packages/adm/model/counter.py:307` · 2026-11-14 — `_getCounter` recycles only when the counter has a `date_field`: `recycle = counter_pars.get('recycle') if date_field else False`. Without a date the key is ignored silently.
- `READ` `projects/gnrcore/packages/adm/model/counter.py:330` · 2026-11-14 — A new number with a date earlier than `last_used` is refused unless `date_tolerant` is set.
- `READ` `projects/gnrcore/packages/adm/model/counter.py:357` · 2026-11-14 — `releaseCounter` reads the number back from the formatted string with `int(sequence[N_start:N_end])`: decimal only.
- `READ` `projects/gnrcore/packages/adm/model/counter.py:103` · 2026-11-14 — `_alignOneSequence` rebuilds `holes` and the counter from the documents; with `fix_duplicate` (line 157) it rewrites the number of a duplicated document by appending `_`.
- `READ` `gnrpy/gnr/app/gnrdbo.py:1573` · 2026-11-14 — `trigger_assignCounters` calls `assignCounterColumn` for every counter column on insert and on update, unless the record goes back to draft; it receives `old_record` but does not pass it on.
- `READ` `gnrpy/gnr/app/gnrdbo.py:1569` · 2026-11-14 — `trigger_releaseCounters` releases only recycling counters, and keeps the number on a return to draft when the counter has `assignIfDraft`.
- `READ` `gnrpy/gnr/app/gnrdbo.py:1586` · 2026-11-14 — `assignCounterColumn` and `releaseCounterColumn` (line 1581) are the only two points where a table calls `adm.counter` to assign or release.
- `READ` `gnrpy/gnr/app/gnrapp.py:1050` · 2026-11-14 — `GnrApp.experimentalValue(group, name)` reads `experimental.group?name` from instanceconfig.xml.

#### Open pull requests on the same code

genropy/genropy#1881 fixes the release between numbers in use with a `LIKE` search on each side. genropy/genropy#1882 adds claiming a number set by hand, listing the free numbers and keeping a number on draft. Both work on the `holes` Bag; this proposal does not depend on them.

### Proposed solution

#### Blocks

The numbers of a series are a contiguous sequence of blocks, without overlaps, from the first number to the last one assigned. A block is either **occupied** (consecutive numbers in use) or **free** (consecutive numbers released). Consecutive numbers in use stay in one block: there is no row per number.

Every block carries its first and last number, and the value of `order_field` of its first and of its last number. For a free block these are the values of the occupied numbers that delimit it.

The idea comes from the timeline of package `tmsh` (gnrwork), where a resource is a sequence of contiguous holes, allocating splits a hole and releasing merges the free neighbours.

**Example — Assign 1, 2, 3, then release 2**

```text
assign 1    occupied 1-1
assign 2    occupied 1-2
assign 3    occupied 1-3
release 2   occupied 1-1 | free 2-2 | occupied 3-3
```

The window of the free block 2-2 goes from the last value of block 1-1 to the first value of block 3-3: both are already stored.

#### Operations

- **New number**: last number of the highest occupied block plus one; the block grows, or a new occupied block starts above a free tail.
- **Recycled number**: the lowest free number whose window holds the record's `order_field` value; its free block shrinks or disappears and merges with the occupied neighbours.
- **Number set by hand**: it splits the block that holds it; refused if it is occupied or outside its window.
- **Release** of number n: n becomes free and merges with the free neighbours. When n lies inside a longer occupied block, the new edges n-1 and n+1 need their `order_field` values: they are read with one equality query on the counter field, using `formatSequence(n-1)` and `formatSequence(n+1)`. Releasing the last number takes the series back to the previous occupied number.
- The triggers act only when the number changes: `trigger_assignCounters` passes `old_record`.
- Every operation runs under the lock of the series record (`for_update` on `adm.counter`).

#### Counter keys

*Keys of counter_<field>() in the new model*

| Key | Meaning |
|---|---|
| `date_field` | Required when the format holds a period (`$YYYY`, `$YY`, `$MM`, `$DD`): it decides the series of the record. It no longer implies an order. |
| `order_field` | Optional. The numbers must follow the order of this field. Dtype `D`: dates are compared, two documents of the same day fit in any order. Dtype `DH` or `DHZ`: the full timestamp is compared. Missing: no order check. |
| `recycle` | Requires `order_field`; without it the configuration is an explicit error. |
| `date_tolerant` | Not used: a counter without `order_field` is tolerant. |

All the other keys keep their meaning: `format`, `code`, `starting_value`, `base`, `assignIfDraft`, `showOnLoad`, `onAssigned`, `onReleased`, `rootstore`.

#### Opt-in and switch of a series

The blocks live in the new table `adm.counters_n`, one row per block, linked to the `adm.counter` record of the series. The new model is opt-in through an experimental switch, read with `experimentalValue('new_counters', 'counters')`: `*` enables it for every counter, a comma-separated list of `pkg.table.field` for the listed ones. `assignCounterColumn` and `releaseCounterColumn` choose between `adm.counter` and the new model; counters not enabled behave as today.

```xml
<experimental>
    <new_counters counters="*"/>
</experimental>
```

1. `analyzeCounter(table, field)`: read-only analysis of every series of the counter, with the errors `not_a_number`, `missing_order_value`, `duplicate`, `wrong_order`. No document is changed.
2. `loadCounter(table, field)`: load of the blocks from the documents, for the clean series only; a series with errors is reported and skipped.
3. The counter is added to the switch.

`checkCounter(table, field)` compares the stored blocks with the documents, read-only, and replaces the checking part of `alignSequences`. `freeSequences(table, field, record)` lists the free numbers of a series with their window. The table that numbers a field is `tblobj.counterTable(field)` in `gnrdbo`; `adm.counters_n` implements `assignCounter`, `releaseCounter` and `guessNextSequence` with the signatures of `adm.counter`.

The order values are stored as ISO text and compared in Python as dates (`D`) or timestamps (`DH`, `DHZ`), so the same columns serve every dtype and every adapter.

#### Not in this proposal

- A PostgreSQL trigger on the document table that keeps the blocks aligned on writes made outside the Python triggers (direct SQL, `insertMany`). Setting a number as occupied twice is harmless, so it can be added later beside the Python path.

### Decisions

- **d-model** `decided` — How are the numbers of a series kept?
   1. **holes Bag in adm.counter, as today**
   2. **One row per assigned number**
   3. **Contiguous blocks, occupied and free, each with first and last number and first and last order value**
   → Choice: **Contiguous blocks, occupied and free, each with first and last number and first and last order value** (GP, 2026-11-14)
- **d-order** `decided` — Which value must the numbers follow?
   1. **Always the date_field, unless date_tolerant**
   2. **order_field, optional; its dtype decides date or full timestamp; missing means no check**
   → Choice: **order_field, optional; its dtype decides date or full timestamp; missing means no check** (GP, 2026-11-14)
- **d-recycle** `decided` — Can a counter recycle without an order?
   1. **Ignore recycle, as today**
   2. **Explicit configuration error**
   → Choice: **Explicit configuration error** (GP, 2026-11-14)
- **d-sql** `decided` — Python triggers or a PostgreSQL trigger?
   1. **Python, on every adapter**
   2. **PostgreSQL trigger on the document table**
   → Choice: **Python, on every adapter** (GP, 2026-11-14)
- **d-storage** `decided` — Where are the blocks stored?
   1. **A new adm table, one row per block, linked to the adm.counter record of its series**
   2. **A new column of adm.counter holding the blocks of its series**
   → Choice: **A new adm table, one row per block, linked to the adm.counter record of its series** (GP, 2026-11-14)
- **d-table-name** `decided` — Name of the table of blocks?
   1. **adm.newcounters**
   2. **adm.counters_n**
   → Choice: **adm.counters_n** (GP, 2026-11-14)
- **d-switch** `decided` — Name and shape of the experimental switch?
   1. **experimentalValue('db', 'counters_n') with a list of counters**
   2. **experimentalValue('new_counters', 'counters'): '*' for every counter, or a list of pkg.table.field**
   → Choice: **experimentalValue('new_counters', 'counters'): '*' for every counter, or a list of pkg.table.field** (GP, 2026-11-14)

### Consequences

- The free numbers and their windows come from the blocks: no `LIKE` search, no query on the document table except at the two new edges of a release inside an occupied block.
- The number is read from the blocks, not parsed back from the formatted string.
- A counter with `date_field` and no `order_field` loses the date check when it moves to the new model: the switch step declares `order_field` where the order is required.
- Writes that skip the Python triggers can still make the blocks drift, as they do with `holes` today.

### Related documents

- `genropy/genropy#1879` — Releasing a number can take the counter back below numbers in use
- `genropy/genropy#1881` — Release counter numbers between the numbers in use
- `genropy/genropy#1882` — Claim a counter number set by hand, list the free numbers
