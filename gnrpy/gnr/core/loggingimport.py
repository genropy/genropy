# -*- coding: utf-8 -*-
"""loggingimport - Hierarchical module import with logging (DEPRECATED).

.. deprecated::
    This module uses the deprecated ``imp`` module which was removed in
    Python 3.12. It also modifies ``builtins.__import__`` which is a
    global side effect. Do not use this module.

This code was intended to be read, not executed. It provides a Python
re-implementation of hierarchical module import that logs each import.

The name is a pun on the klunkier predecessor of this module, "ni".

Warning:
    Importing this module has global side effects: it replaces the
    built-in ``__import__`` and ``reload`` functions.

Note:
    This module has ZERO callers in the codebase and should be removed.
"""

from __future__ import annotations

# REVIEW:DEAD — entire module is unused (zero imports in codebase)
# REVIEW:COMPAT — uses deprecated `imp` module (removed in Python 3.12)
# REVIEW:SMELL — modifies builtins.__import__ as side effect on import

import builtins
import sys
from types import ModuleType
from typing import Any

# The imp module is deprecated since Python 3.4 and removed in 3.12
try:
    import imp  # type: ignore[import-deprecated]
except ImportError:
    imp = None  # type: ignore[assignment]


def import_hook(
    name: str,
    globals: dict[str, Any] | None = None,
    locals: dict[str, Any] | None = None,
    fromlist: list[str] | None = None,
    level: int = -1,
) -> ModuleType:
    """Replacement for __import__() that logs imports.

    Args:
        name: The name of the module to import.
        globals: The global namespace (used to determine parent package).
        locals: The local namespace (unused).
        fromlist: Names to import from the module.
        level: Specifies whether to use absolute or relative imports.

    Returns:
        The imported module.

    Raises:
        ImportError: If the module cannot be found.
    """
    print("Importing " + name)
    parent = determine_parent(globals)
    q, tail = find_head_package(parent, name)
    m = load_tail(q, tail)
    if not fromlist:
        return q
    if hasattr(m, "__path__"):
        ensure_fromlist(m, fromlist)
    return m


def determine_parent(globals: dict[str, Any] | None) -> ModuleType | None:
    """Determine the parent package from globals.

    Args:
        globals: The global namespace dictionary.

    Returns:
        The parent module or None.
    """
    if not globals or "__name__" not in globals:
        return None
    pname = globals["__name__"]
    if "__path__" in globals:
        parent = sys.modules[pname]
        assert globals is parent.__dict__
        return parent
    if "." in pname:
        i = pname.rfind(".")
        pname = pname[:i]
        parent = sys.modules[pname]
        assert parent.__name__ == pname
        return parent
    return None


def find_head_package(
    parent: ModuleType | None,
    name: str,
) -> tuple[ModuleType, str]:
    """Find the head package of a dotted module name.

    Args:
        parent: The parent module or None.
        name: The full module name.

    Returns:
        A tuple of (head_module, remaining_tail).

    Raises:
        ImportError: If the head package cannot be found.
    """
    if "." in name:
        i = name.find(".")
        head = name[:i]
        tail = name[i + 1 :]
    else:
        head = name
        tail = ""
    if parent:
        qname = "%s.%s" % (parent.__name__, head)
    else:
        qname = head
    q = import_module(head, qname, parent)
    if q:
        return q, tail
    if parent:
        qname = head
        parent = None
        q = import_module(head, qname, parent)
        if q:
            return q, tail
    raise ImportError("No module named " + qname)


def load_tail(q: ModuleType, tail: str) -> ModuleType:
    """Load the remaining tail of a dotted module name.

    Args:
        q: The head module.
        tail: The remaining dotted name.

    Returns:
        The final module.

    Raises:
        ImportError: If a submodule cannot be found.
    """
    m = q
    while tail:
        i = tail.find(".")
        if i < 0:
            i = len(tail)
        head, tail = tail[:i], tail[i + 1 :]
        mname = "%s.%s" % (m.__name__, head)
        m = import_module(head, mname, m)
        if not m:
            raise ImportError("No module named " + mname)
    return m


def ensure_fromlist(
    m: ModuleType,
    fromlist: list[str],
    recursive: int = 0,
) -> None:
    """Ensure all names in fromlist are available on the module.

    Args:
        m: The module to check.
        fromlist: List of names to ensure are importable.
        recursive: Flag to prevent infinite recursion with __all__.
    """
    for sub in fromlist:
        if sub == "*":
            if not recursive:
                try:
                    all_names = m.__all__
                except AttributeError:
                    pass
                else:
                    ensure_fromlist(m, all_names, 1)  # type: ignore[arg-type]
            continue
        if sub != "*" and not hasattr(m, sub):
            subname = "%s.%s" % (m.__name__, sub)
            submod = import_module(sub, subname, m)
            if not submod:
                raise ImportError("No module named " + subname)


def import_module(
    partname: str,
    fqname: str,
    parent: ModuleType | None,
) -> ModuleType | None:
    """Import a single module.

    Args:
        partname: The partial name (last component).
        fqname: The fully qualified name.
        parent: The parent module or None.

    Returns:
        The imported module or None if not found.
    """
    try:
        return sys.modules[fqname]
    except KeyError:
        pass

    if imp is None:
        return None

    try:
        fp, pathname, stuff = imp.find_module(
            partname, parent and hasattr(parent, "__path__") and parent.__path__
        )
    except ImportError:
        return None
    try:
        m = imp.load_module(fqname, fp, pathname, stuff)
    finally:
        if fp:
            fp.close()
    if parent:
        setattr(parent, partname, m)
    return m


def reload_hook(module: ModuleType) -> ModuleType | None:
    """Replacement for reload().

    Args:
        module: The module to reload.

    Returns:
        The reloaded module.
    """
    name = module.__name__
    if "." not in name:
        return import_module(name, name, None)
    i = name.rfind(".")
    pname = name[:i]
    parent = sys.modules[pname]
    return import_module(name[i + 1 :], name, parent)


# Save the original hooks
original_import = builtins.__import__
original_reload = getattr(builtins, "reload", None)  # reload not in Python 3

# Now install our hooks (SIDE EFFECT ON IMPORT!)
# REVIEW:SMELL — these lines execute on import, modifying global state
builtins.__import__ = import_hook  # type: ignore[assignment]
if original_reload is not None:
    builtins.reload = reload_hook  # type: ignore[attr-defined]


__all__ = [
    "import_hook",
    "determine_parent",
    "find_head_package",
    "load_tail",
    "ensure_fromlist",
    "import_module",
    "reload_hook",
    "original_import",
    "original_reload",
]
