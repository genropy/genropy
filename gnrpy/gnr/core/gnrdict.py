# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy core - see LICENSE for details
# module gnrdict : gnrdict implementation
# Copyright (c) : 2004 - 2007 Softwell sas - Milano
# Written by    : Giovanni Porcari, Michele Bertoldi
#                 Saverio Porcari, Francesco Porcari , Francesco Cavazzana
# --------------------------------------------------------------------------
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
"""Dictionary utilities for GenroPy.

This module provides specialized dictionary classes and utility functions
for working with dictionaries in GenroPy applications:

- :func:`dictExtract`: Extract items with keys matching a prefix.
- :class:`FakeDict`: Empty dict subclass for type discrimination.
- :class:`UnionDict`: Read-only union view of multiple dictionaries.
- :class:`GnrDict`: Ordered dictionary with index-based and ``#N`` key access.
- :class:`GnrNumericDict`: GnrDict variant with numeric index iteration.
"""

from __future__ import annotations

import warnings
from collections.abc import Callable, Iterable, Iterator, Mapping
from itertools import chain
from typing import Any, TypeVar

_KT = TypeVar("_KT")
_VT = TypeVar("_VT")


def dictExtract(
    mydict: dict[str, Any],
    prefix: str,
    pop: bool = False,
    slice_prefix: bool = True,
    is_list: bool = False,  # REVIEW:UNUSED — parameter is never used
) -> dict[str, Any]:
    """Extract items from a dictionary whose keys start with a given prefix.

    This function filters a dictionary to include only items whose keys
    begin with the specified prefix. Optionally removes those items from
    the source dictionary and/or removes the prefix from the resulting keys.

    Args:
        mydict: The source dictionary to extract from.
        prefix: The prefix to match against dictionary keys.
        pop: If True, removes matching items from the source dictionary.
            Defaults to False.
        slice_prefix: If True, removes the prefix from keys in the result.
            Defaults to True.
        is_list: Unused parameter (kept for backward compatibility).

    Returns:
        A new dictionary containing only the items whose keys started with
        the prefix. If ``slice_prefix`` is True, the prefix is removed from
        the keys. Keys that would become Python reserved words (like 'class')
        are prefixed with an underscore.

    Examples:
        >>> d = {'user_name': 'John', 'user_age': 30, 'item_id': 1}
        >>> dictExtract(d, 'user_')
        {'name': 'John', 'age': 30}
        >>> dictExtract(d, 'user_', slice_prefix=False)
        {'user_name': 'John', 'user_age': 30}
    """
    lprefix = len(prefix) if slice_prefix else 0

    cb = mydict.pop if pop else mydict.get
    reserved_names = ["class"]
    return dict(
        [
            (
                k[lprefix:]
                if k[lprefix:] not in reserved_names
                else "_%s" % k[lprefix:],
                cb(k),
            )
            for k in list(mydict.keys())
            if k.startswith(prefix)
        ]
    )


class FakeDict(dict[_KT, _VT]):  # REVIEW:DEAD — no external callers found (only tests)
    """Empty dict subclass for type discrimination.

    This class exists solely as a marker type to distinguish certain
    dictionary instances from plain dicts. It has no additional behavior.
    """

    pass


class UnionDict(Mapping[_KT, _VT]):  # REVIEW:DEAD — no external callers found
    """Read-only union view of multiple dictionaries.

    Provides a unified view over multiple dictionaries without copying
    their contents. When a key is looked up, dictionaries are searched
    in order and the first match is returned.

    Attributes:
        dicts: Tuple of underlying dictionaries.

    Examples:
        >>> d1 = {'a': 1, 'b': 2}
        >>> d2 = {'b': 3, 'c': 4}
        >>> u = UnionDict(d1, d2)
        >>> u['a']
        1
        >>> u['b']  # d1 takes precedence
        2
        >>> u['c']
        4
    """

    def __init__(self, *dicts: dict[_KT, _VT]) -> None:
        """Initialize with one or more dictionaries.

        Args:
            *dicts: Variable number of dictionaries to unify.
        """
        self.dicts: tuple[dict[_KT, _VT], ...] = dicts

    def __getitem__(self, key: _KT) -> _VT:
        """Get a value by key, searching dictionaries in order.

        Args:
            key: The key to look up.

        Returns:
            The value from the first dictionary containing the key.

        Raises:
            KeyError: If the key is not found in any dictionary.
        """
        for d in self.dicts:
            if key in d:
                return d[key]
        raise KeyError(key)

    def __iter__(self) -> Iterator[_KT]:
        """Iterate over all unique keys from all dictionaries.

        Returns:
            An iterator over unique keys, preserving first-seen order.
        """
        # dict.fromkeys removes duplicates while preserving order
        return iter(dict.fromkeys(chain.from_iterable(self.dicts)))

    def __len__(self) -> int:
        """Return the number of unique keys across all dictionaries.

        Returns:
            The count of unique keys.
        """
        return len(dict.fromkeys(chain.from_iterable(self.dicts)))

    def __repr__(self) -> str:
        """Return a string representation as a plain dict.

        Returns:
            String representation of the unified dictionary.
        """
        return f"{dict(self)}"


class GnrDict(dict[str, _VT]):
    """Ordered dictionary with index-based key access.

    A dictionary that maintains insertion order and supports accessing
    items by their numeric position using the ``#N`` syntax in keys.

    The class predates Python 3.7's ordered dict guarantee and provides
    additional features like index-based access, arithmetic operations
    on dictionaries, and in-place sorting.

    Attributes:
        _list: Internal list maintaining key order.

    Examples:
        >>> d = GnrDict()
        >>> d['first'] = 1
        >>> d['second'] = 2
        >>> d['#0']  # Access by index
        1
        >>> d['#1']
        2
        >>> d.keys()
        ['first', 'second']
    """

    def __init__(
        self,
        *args: dict[str, _VT] | Iterable[tuple[str, _VT]],
        **kwargs: _VT,
    ) -> None:
        """Initialize from optional mapping/iterable and keyword arguments.

        Args:
            *args: Optional source data - either a dict or an iterable
                of (key, value) pairs.
            **kwargs: Additional key-value pairs to include.
        """
        dict.__init__(self)
        self._list: list[str] = []
        if args:
            source = args[0]
            if hasattr(source, "items"):
                [self.__setitem__(k, v) for k, v in list(source.items())]
            else:
                [self.__setitem__(k, v) for k, v in source]
        if kwargs:
            [self.__setitem__(k, v) for k, v in list(kwargs.items())]

    def __setitem__(self, key: str, value: _VT) -> None:
        """Set a key-value pair, maintaining order.

        Args:
            key: The key (may use ``#N`` syntax for index-based access).
            value: The value to set.
        """
        key = self._label_convert(key)
        if key not in self:
            self._list.append(key)
        dict.__setitem__(self, key, value)

    def __iter__(self) -> Iterator[str]:
        """Iterate over keys in insertion order.

        Returns:
            An iterator over the keys.
        """
        return self._list.__iter__()

    def __delitem__(self, key: str) -> None:
        """Delete an item by key.

        Args:
            key: The key to delete (may use ``#N`` syntax).
        """
        key = self._label_convert(key)
        self._list.remove(key)
        dict.__delitem__(self, key)

    def get(self, label: str, default: _VT | None = None) -> _VT | None:
        """Get a value by key with optional default.

        Args:
            label: The key to look up (may use ``#N`` syntax).
            default: Value to return if key is not found.

        Returns:
            The value for the key, or default if not found.
        """
        return dict.get(self, self._label_convert(label), default)

    def __getitem__(self, label: str) -> _VT:
        """Get a value by key.

        Args:
            label: The key to look up (may use ``#N`` syntax).

        Returns:
            The value for the key.

        Raises:
            KeyError: If the key is not found.
        """
        # REVIEW:SMELL — comment mentions slice support not implemented
        return dict.__getitem__(self, self._label_convert(label))

    def _label_convert(self, label: str) -> str:
        """Convert ``#N`` style labels to actual keys.

        If the label starts with ``#`` followed by digits, it is treated
        as an index into the key list.

        Args:
            label: The label to convert.

        Returns:
            The actual key (converted from index if applicable).
        """
        try:
            if label.startswith("#") and label[1:].isdigit():
                label = self._list[int(label[1:])]
        except Exception:  # REVIEW:SMELL — bare except catches too much
            pass
        return label

    def items(self) -> list[tuple[str, _VT]]:
        """Return a list of (key, value) pairs in order.

        Returns:
            List of key-value tuples.
        """
        return [(k, self[k]) for k in self._list]

    def keys(self) -> list[str]:
        """Return a list of keys in order.

        Returns:
            List of keys.
        """
        return list(self._list)

    def index(self, value: str) -> int:
        """Return the index of a key in the ordered list.

        Args:
            value: The key to find.

        Returns:
            The index of the key, or -1 if not found.
        """
        if value in self._list:
            return self._list.index(value)
        return -1

    def values(self) -> list[_VT]:
        """Return a list of values in key order.

        Returns:
            List of values.
        """
        return [self[k] for k in self._list]

    def pop(self, key: str, dflt: _VT | None = None) -> _VT | None:
        """Remove and return a value by key.

        Args:
            key: The key to remove (may use ``#N`` syntax).
            dflt: Default value if key is not found.

        Returns:
            The removed value, or dflt if key not found.
        """
        key = self._label_convert(key)
        if key in self._list:
            self._list.remove(key)
            return dict.pop(self, key)
        return dflt

    def __str__(self) -> str:
        """Return a string representation.

        Returns:
            String in dict-like format with items in order.
        """
        return "{%s}" % (
            ", ".join(["%s: %s" % (repr(k), repr(self[k])) for k in self._list])
        )

    __repr__ = __str__

    def clear(self) -> None:
        """Remove all items from the dictionary."""
        self._list[:] = []
        dict.clear(self)

    def update(  # type: ignore[override]
        self,
        o: dict[str, _VT],
        removeNone: bool = False,
    ) -> None:
        """Update the dictionary with items from another dict.

        Args:
            o: Dictionary to update from.
            removeNone: If True, remove keys whose values are None after update.
        """
        [self.__setitem__(k, v) for k, v in list(o.items())]
        if removeNone:
            [self.__delitem__(k) for k, v in list(o.items()) if v is None]

    def copy(self) -> GnrDict[_VT]:
        """Return a shallow copy.

        Returns:
            A new GnrDict with the same items.
        """
        return GnrDict(self)

    def setdefault(self, key: str, d: _VT | None = None) -> _VT | None:
        """Set a key to a default value if not present.

        Args:
            key: The key to set (may use ``#N`` syntax).
            d: Default value to set if key is not present.

        Returns:
            The value for the key (existing or newly set).
        """
        key = self._label_convert(key)
        if key not in self:
            self.__setitem__(key, d)
        return self[key]

    def popitem(self) -> tuple[str, _VT]:
        """Remove and return the last (key, value) pair.

        Returns:
            Tuple of (key, value) for the last item.

        Raises:
            IndexError: If the dictionary is empty.
        """
        k = self._list.pop()
        return (k, dict.pop(self, k))

    def iteritems(self) -> Iterator[tuple[str, _VT]]:
        """Iterate over (key, value) pairs in order.

        Returns:
            An iterator over key-value tuples.
        """
        for k in self._list:
            yield (k, self[k])

    def iterkeys(self) -> Iterator[str]:
        """Iterate over keys in order.

        Returns:
            An iterator over keys.
        """
        for k in self._list:
            yield k

    def itervalues(self) -> Iterator[_VT]:
        """Iterate over values in key order.

        Returns:
            An iterator over values.
        """
        for k in self._list:
            yield self[k]

    def __add__(self, o: dict[str, _VT]) -> GnrDict[_VT]:
        """Return a new GnrDict with items from both dicts.

        Args:
            o: Dictionary to add.

        Returns:
            New GnrDict with combined items.
        """
        return GnrDict(list(self.items()) + list(o.items()))

    def __sub__(self, o: dict[str, Any]) -> GnrDict[_VT]:
        """Return a new GnrDict excluding keys present in o.

        Args:
            o: Dictionary whose keys should be excluded.

        Returns:
            New GnrDict with items not in o.
        """
        return GnrDict([(k, self[k]) for k in self if k not in o])

    def __getslice__(  # REVIEW:COMPAT — deprecated since Python 2
        self,
        start: int | None = None,
        end: int | None = None,
    ) -> GnrDict[_VT]:  # pragma: no cover
        """Return a slice of the dictionary by key index.

        Deprecated since Python 2. Use explicit slicing instead.

        Args:
            start: Start index (inclusive).
            end: End index (exclusive).

        Returns:
            New GnrDict with the sliced items.
        """
        warnings.warn("__getslice__ is deprecated since Python2")
        return GnrDict([(k, self[k]) for k in self._list[start:end]])

    def __setslice__(  # REVIEW:COMPAT — deprecated since Python 2
        self,
        start: int | None = None,
        end: int | None = None,
        val: dict[str, _VT] | GnrDict[_VT] | None = None,
    ) -> None:  # pragma: no cover
        """Replace a slice of the dictionary.

        Deprecated since Python 2. Use explicit slicing instead.

        Args:
            start: Start index (inclusive).
            end: End index (exclusive).
            val: Dictionary of new values.
        """
        warnings.warn("__getslice__ is deprecated since Python2")
        [dict.__delitem__(self, k) for k in self._list[start:end]]
        val = GnrDict(val)
        key_list = list(self._list)
        newkeys = list(val.keys())
        newkeysrange = list(range(start, start + len(newkeys)))
        key_list[start:end] = newkeys
        self._list[:] = [
            x for i, x in enumerate(key_list) if (x not in newkeys) or i in newkeysrange
        ]
        dict.update(self, val)

    def reverse(self) -> None:
        """Reverse the order of keys in place."""
        self._list.reverse()

    def sort(
        self,
        cmpfunc: Callable[[str], Any] | None = None,
        reverse: bool = False,
    ) -> None:
        """Sort the dictionary keys in place.

        Args:
            cmpfunc: Key function for sorting (passed to ``list.sort(key=...)``).
            reverse: If True, sort in descending order.
        """
        self._list.sort(key=cmpfunc, reverse=reverse)


class GnrNumericDict(
    GnrDict[_VT]
):  # REVIEW:DEAD — no external callers found (only tests)
    """GnrDict variant with numeric index iteration.

    Like GnrDict, but ``__getitem__`` with an integer directly accesses
    by index, and iteration yields values instead of keys.
    """

    def __getitem__(self, label: int | str) -> _VT:
        """Get a value by key or numeric index.

        Args:
            label: Either a string key or an integer index.

        Returns:
            The value at the specified key or index.
        """
        if isinstance(label, int):
            return dict.__getitem__(self, self._list[label])
        else:
            return dict.__getitem__(self, self._label_convert(label))

    def __iter__(self) -> Iterator[_VT]:
        """Iterate over values instead of keys.

        Returns:
            An iterator over the values.
        """
        for k in self._list:
            yield self[k]
