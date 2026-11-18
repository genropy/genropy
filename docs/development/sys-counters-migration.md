# Moving an instance to sys.counter

`sys.counter` (#1890) numbers the counters of a table (`counter_<field>(record)`)
as blocks of occupied and free numbers, instead of the `counter` and `holes` of
`adm.counter`. It is opt-in, per instance, through an experimental switch;
`adm.counter` is unchanged and keeps numbering every counter the switch does
not name. The design is in `xmldocs/proposal/sys-counters`.

## What changes for a counter

- `order_field` sets the order the numbers follow; without it the order is the
  `date_field`, unless the counter is `date_tolerant`.
- `recycle=True` requires an order. With `counters="*"` a recycling counter
  without an order stays on `adm.counter`; naming it explicitly is a
  configuration error.
- Code that calls `adm.counter.assignCounter` directly keeps numbering in
  `adm.counter`.

## Application code works on both counters

An instance can switch only when its application code never calls
`adm.counter` or `sys.counter` directly and never asks which one numbers a
field. `gnrdbo.TableBase` gives the operations, and each counter implements
them:

- `assignCounterColumn`, `releaseCounterColumn`, `guessCounter`: a new number,
  a number given back, the next number. A number set in the record before the
  save is claimed by both counters: refused when another record holds it.
- `realignCounterColumn(field, record=None, floor=None)`: forget the stored
  state of a series (or of every series of the field) and rebuild it from the
  numbers in the table, instead of deleting or updating `adm.counter` rows.
- `freeCounterSequences(field, record)`, `lastCounterSequence(field, record)`,
  `formatCounterSequence(field, record, number)`: the free numbers with their
  dates, the last number and its date, a number formatted, for a choice of the
  number made by the user.

A counter assigned twice in one save (the table trigger calls
`trigger_assignCounters`, then the save calls it again) works on both
counters: the number is refused only when another record holds it. What follows
the number goes in `onAssigned` of `counter_<field>`.

## Steps

1. **Update the database.** The two tables `sys.counter` and
   `sys.counter_block` are created by the usual model update:

   ```
   gnr app dbsetup <instance>
   ```

2. **Analyse, before switching on.** Nothing is written without `--load`;
   `--counters` replaces the switch, so this runs on an instance still
   numbering with `adm.counter`:

   ```
   gnr @<instance> sys migrate_counters --counters '*'
   ```

   One line per counter and period, with the count of the numbers in use and a
   status:

   | Status | Meaning |
   |---|---|
   | `not_loaded` | The period has no blocks yet: `--load` builds them |
   | `loaded` | Built by this run |
   | `ok` | The stored blocks match the table |
   | `errors` | The numbers in the table are not consistent (`not_a_number`, `missing_order_value`, `duplicate`, `wrong_order`), or a recycling counter has no order (`recycle_without_order`): the period is never loaded |
   | `blocks_differ`, `missing_from_blocks` | The stored blocks differ from the table, e.g. after writes that skipped the Python triggers |

   `--table pkg.table` (repeatable) restricts the run. The command exits with
   code 2 when a period is in `errors`.

3. **Fix the periods in `errors`.** A period that is not consistent cannot be
   loaded, and once the switch is on its first save is refused. Fix the
   records named in the report, then run step 2 again until no period is in
   `errors`.

4. **Switch on.** In the instance's `instanceconfig.xml`:

   ```xml
   <experimental>
       <new_counters counters="*"/>
   </experimental>
   ```

   or a list, to move some counters only:
   `counters="invc.invoice.inv_number,invc.order.ord_number"`. Restart the
   instance.

5. **Load and check.**

   ```
   gnr @<instance> sys migrate_counters --load
   ```

   It builds the blocks of the periods not loaded yet and checks every period:
   every line should read `loaded` or `ok`. A period left unloaded would be
   loaded anyway the first time it numbers a record; loading it here checks
   it before a user meets the error.

   The same report is the action *Move counters to sys.counter* of the
   adm counter page (superadmin), with a *Load* checkbox.

A counter that does not recycle keeps the numbers `adm.counter` gave above the
highest one still in the table: a number deleted at the tail is never given
again.

## Going back

Remove the `new_counters` node (or a counter from its list) and restart.
`adm.counter` does not know the numbers given meanwhile: rebuild its `counter`
and `holes` with the action *Initialize counter* of the adm counter page
(`alignSequences`) before the next save.
