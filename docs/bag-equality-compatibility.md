# JavaScript Bag equality compatibility

The GenroJS mixin overrides `isEqual(other)` with the legacy identity/location
contract: the same instance compares equal, as do two Bags whose parent nodes
have equal `_id` values. Null/undefined and unrelated objects compare false.
Equal contents in distinct detached Bags do not imply equality.

Standalone JavaScript Bag `equalTo(other)` compares contents, including nested
framework Bags, independently of the compatibility `isEqual` method. Python uses
`__eq__` for content equality and is unchanged. This override preserves the
framework's global `isEqual(a, b)` delegation without changing its call sites.

The standalone Bag no longer exposes `isEqual`. Its `equalTo(null)` and other
non-Bag comparisons return false.
