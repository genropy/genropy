<!-- generated from sys-counters.xml by xmldocs: do not edit, edit the XML -->

## sys.counter: counter numbers kept as blocks, opt-in per counter
*Proposal · sys-counters · 2026-11-15 · draft*

### Problem

A recycling counter (`recycle=True`) keeps its free numbers in the `holes` Bag of its `adm.counter` record. The Bag is a second copy of what the document table already says and drifts from it (genropy/genropy#1879); `alignSequences` rebuilds it, rewriting documents with `fix_duplicate`.

The goal is a numbering service, at the level of the `sys` package, whose state is easy to keep consistent and to query, and which keeps the API of a counter: `counter_<field>(record)`, `assignCounterColumn`, `releaseCounterColumn`, `guessCounter`.

### Current state

- `READ` `gnrpy/gnr/sql/gnrsql/write.py:158` · 2026-11-15 — The SQL layer calls `trigger_assignCounters` on insert and update (line 259) and `trigger_releaseCounters` on delete (line 319); their base versions are empty.
- `READ` `gnrpy/gnr/app/gnrdbo.py:1573` · 2026-11-15 — `gnrdbo` overrides those triggers and calls `adm.counter` from `assignCounterColumn`, `releaseCounterColumn`, `guessCounter` and `_sequencesOnLoading`: four call sites, the only ones that pick the numbering table.
- `READ` `projects/gnrcore/packages/adm/main.py:20` · 2026-11-15 — Package `adm` requires `gnrcore:sys`; `sys` had no table named `counter` or `counter_block`.

genropy/genropy#1888 implemented the same block model inside `adm`; its review (fporcari, 2026-11-14) found four bugs and the overlap with `adm.counter` and genropy/genropy#1882. This proposal is the alternative to it.

### Proposed solution

#### Tables

- `sys.counter`: one row per counter (`pkg`, `tbl`, `fld`, `code`), with no period. Its row is the lock of every operation on the counter.
- `sys.counter_block`: one row per block, with the `period` of the block. A block is a run of consecutive numbers, occupied or free, with `order_first` and `order_last`: the order key of its first and last number; for a free block, those of the occupied numbers around it.

Order keys are integers that sort as the values: `YYYYMMDD` for a date, milliseconds since the epoch in UTC for a timestamp. A free number for a value is a plain query on `sys.counter_block`.

Work happens on the current period, so a lock per counter instead of per period changes little: only saves on other periods wait for it.

#### Counter keys

*Keys of counter_<field>() in the new model*

| Key | Meaning |
|---|---|
| `date_field` | Required when the format holds a period: it decides the period of the record. |
| `order_field` | Optional. The numbers follow its order: dates for a `D` column, the timestamp for `DH`/`DHZ`. Missing: the order is the `date_field`, as with `adm.counter`. |
| `date_tolerant` | As with `adm.counter`: without `order_field`, no order is checked. |
| `recycle` | Requires an order: `order_field`, or a `date_field` without `date_tolerant`. A `date_tolerant` counter recycles without one: its lowest free number, whatever the order of the record. |
| `releaseOnDraft` | Default `True`. When false, a record going back to draft keeps its number. `counter_<field>(record)` may compute it from the record. Read by `gnrdbo.trigger_releaseCounters`, so it holds for `adm.counter` too. |

#### Operations

- **New number**: the lowest free number whose window holds the record's order key, for a recycling counter (the lowest free number, for a `date_tolerant` one); otherwise the last number of the period plus one.
- **Number set by hand** (insert, or changed on update): it splits the block that holds it; refused if occupied or outside its window. A value that is not a number of the series is left alone.
- **Release**: the number becomes free and merges with free neighbours; a split reads the order key of the two new edges from the table. A neighbour missing from the table becomes an open bound and is left to `checkCounter`.
- A number changed or cleared on update releases the old one in the period of the stored record. `trigger_assignCounters` passes `old_record`.
- **A period without blocks** is loaded from the numbers already in the table, under the lock, the first time it is used. For a counter that does not recycle, the numbers `adm.counter` gave above the highest one still in the table stay occupied: a number deleted at the tail is never given again. A period whose numbers are inconsistent is refused, naming `analyzeCounter`.
- **The counter row** is created with `INSERT ... ON CONFLICT DO NOTHING`: two first saves of a counter do not fail, and no failed statement rolls back the save.
- **Guess** (`guessCounter`, `showOnLoad`): a record not inserted yet takes now as a missing timestamp; with a missing date it is not recycled.

#### Switch

```xml
<experimental>
    <new_counters counters="*"/>
</experimental>
```

`experimentalValue('new_counters', 'counters')`: a list of `pkg.table.field` sends those counters to `sys.counter`; `*` sends every counter except a recycling one without an order that is not `date_tolerant`, which stays on `adm.counter`. Such a counter, listed, is a configuration error. `gnrdbo.sysCounter(field, record)` makes the choice; `adm.counter` is not changed.

`analyzeCounter`, `loadCounter` and `checkCounter` report, load and verify every period of a counter; `freeSequences` lists the free numbers of a period with their window. `checkCounter` reports `not_loaded` for a period without blocks, `blocks_differ` for a recycling counter whose blocks differ from the table, and `missing_from_blocks` for a counter that does not recycle when a number of the table is not occupied in the blocks.

### Decisions

- **d-level** `decided` — Where does the numbering service live?
   1. **Inside adm.counter (genropy/genropy#1888)**
   2. **New tables sys.counter and sys.counter_block**
   → Choice: **New tables sys.counter and sys.counter_block** (GP, 2026-11-15)
- **d-header** `decided` — One header per period or per counter?
   1. **One per period, as adm.counter**
   2. **One per counter; the period on the blocks**
   → Choice: **One per counter; the period on the blocks** (GP, 2026-11-15)
- **d-dbo** `decided` — Change gnrdbo or bypass it?
   1. **Change the four call sites of gnrdbo**
   2. **A service called from write.py; guessCounter and _sequencesOnLoading would still need gnrdbo**
   → Choice: **Change the four call sites of gnrdbo** (GP, 2026-11-15)

### Consequences

- Code that calls `adm.counter.assignCounter` directly keeps numbering in `adm.counter`.
- Turning the switch off sends the counter back to `adm.counter`, whose `counter` and `holes` do not know the numbers given meanwhile: `alignSequences` rebuilds them.
- Writes that skip the Python triggers can still make the blocks drift; `checkCounter` reports it.

### Related documents

- `genropy/genropy#1888` — The same block model inside adm.counter
- `genropy/genropy#1879` — Releasing a number can take the counter back below numbers in use
