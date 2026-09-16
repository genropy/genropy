# Process-local Python Bag selection

The instance setting `experimental/bag@implementation` is resolved when `gnr` is
first imported. `_bag_mode` retains that selection for the lifetime of the
process, including module reloads. Editing configuration or assigning to the
public `gnr.BAG_MODE` status attribute does not switch implementations. Restart
all associated processes to change the selection.

In `genro-bag` mode, `nativebag.activate()` publishes one facade at
`gnr.core.gnrbag`. Normal imports get the selected standalone classes and the
existing compatibility exports. A narrowly scoped meta-path finder handles only
that module name: a reload or an import after cache removal returns the same
facade and class identities. The legacy source file checks the fixed selection
before defining its classes, including when loaded through a file-location spec
under an alternate name. A process selected as legacy cannot activate native
Bags later, even if it has not yet imported `gnr.core.gnrbag`.

Ordinary assignment or deletion of the facade's class exports raises
`ActivationError` immediately, including assignments made inside mixin hooks.
Adding methods to application subclasses and using normal GenroPy class/instance
mixins remain supported. Legacy mode retains the ordinary module and does not
import the standalone dependency or install the native finder.

The previous recursive inspection of function globals, closures and class MROs
at each `classMixin`, `instanceMixin` and `cloneClass` operation has been removed.
Selection is enforced at startup and import, without work proportional to all
methods already accumulated on each target. Wildcard mixing of the facade still
uses its explicit export list.

This protects supported import paths and normal module assignments; it is not a
security boundary against code deliberately rewriting private module state,
`sys.modules`, module dictionaries or executing edited copies of source files.
No live migration of existing legacy objects is attempted.

Tests use fresh processes for legacy/native configuration, alternate source-file
loads, facade and configuration reloads, cache removal, late activation, export
mutation from mixin hooks, real SQL queries and ordinary mixin composition. The
former stale-reference simulation changed `gnr.BAG_MODE` to execute the legacy
file; that load is now rejected before any legacy classes can be defined.
