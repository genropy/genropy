# Bag integration — where the notes are

The working notes of the standalone Bag integration (#1348) are not in this
repository: the decision register, the accepted breaking changes of the
browser Bag, the call site audits, the verification checkpoints and the
description of the experimental JSON/TYTX transport live in **genropy_meta**,
under `notes/bag-integration/`, next to the machine produced inventories under
`audit/bag/`.

They were moved there because they are the reasoning behind the change,
addressed to whoever carries the work forward, and they would otherwise age
in the code repository at the first refactoring. Documentation addressed to
whoever uses the framework stays here.

The scripts that produce the inventories stay here as well, in `gnrjs/tests/`:
`bag_audit_callsites.py`, `bag_audit_inventory.cjs` and
`mixin_missing_callsites.py`.
