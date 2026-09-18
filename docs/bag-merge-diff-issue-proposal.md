# Issue proposal: reassess merge and diff for equivalent Python and JavaScript Bag APIs

Status: deferred design review; no implementation approved.

## Purpose

Evaluate the practical usefulness of `merge` and `diff` together and decide
whether to introduce or fully reintroduce them with equivalent capabilities
in the new Python and JavaScript libraries. Functional parity across languages
is the guiding requirement; historical usage alone does not define the API.

## Current decision

`merge` is absent from the new JavaScript Bag and its compatibility mixin.
The legacy JavaScript method was an empty placeholder, not an implementation.
Python retains the historical implementation in its compatibility mixin.
Do not add a JavaScript placeholder or promote the Python compatibility
implementation into the shared native contract pending this review.
No change to `diff` is made by this decision.

## Evidence

The legacy Python merge builds a result Bag recursively and independently
controls addition and updating of values and attributes. `update` modifies
its receiver and does not expose those four independent controls.
The verified production caller is `GnrStructData.load`, using default options;
no other application callers or selective-option uses were found in the
indexed search and local checkout reviewed on 2026-09-17. External unindexed
applications are not covered.

## Questions for the future review

- Identify concrete use cases for selective merging and structural differences.
- Decide whether these capabilities warrant public APIs beyond `update`,
  replacement, copying and equality.
- Define recursion, label matching, ordering, attributes, tags, missing versus
  null values, and resolver handling without accidental resolver execution.
- Define result structure, ownership, copying and mutation guarantees.
- Decide whether a diff is informational or can be applied as a patch, and
  whether any relationship with merge is useful rather than assumed.
- If accepted, implement equivalent contracts in Python and JavaScript with
  shared examples and corresponding tests; keep legacy deviations in mixins.

## Completion criteria

Record a documented accept/reject decision. If accepted, specify and verify
both implementations before calling the capability part of the common API.
