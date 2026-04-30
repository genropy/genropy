# -*- coding: utf-8 -*-
#--------------------------------------------------------------------------
# package       : GenroPy core - see LICENSE for details
# module gnrlist : gnr list implementation
# Copyright (c) : 2004 - 2007 Softwell sas - Milano
# Written by    : Giovanni Porcari, Michele Bertoldi
#                 Saverio Porcari, Francesco Porcari , Francesco Cavazzana
#--------------------------------------------------------------------------
#This library is free software; you can redistribute it and/or
#modify it under the terms of the GNU Lesser General Public
#License as published by the Free Software Foundation; either
#version 2.1 of the License, or (at your option) any later version.

#This library is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
#Lesser General Public License for more details.

#You should have received a copy of the GNU Lesser General Public
#License along with this library; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA


"""
Some useful operations on lists.
"""
import warnings
from functools import cmp_to_key

from gnr.core.gnrdecorator import deprecated


# FIXME: what's this for?
class FakeList(list):
    pass


def findByAttr(l, **kwargs):
    """Find elements in the ``l`` list having attributes with names and values as
    kwargs items. Return the list's attributes

    :param l: the list"""
    result = list(l)
    for k, v in list(kwargs.items()):
        result = [x for x in result if getattr(x, k, None) == v]
    return result


def hGetAttr(obj, attr):
    """Hierarchical get attribute - traverse nested object attributes using dot notation.

    :param obj: the object to get the attribute from
    :param attr: attribute path, can be hierarchical using dots (e.g., 'user.profile.name')
    :return: the attribute value or None if not found
    """
    if obj is None:
        return None
    if '.' not in attr:
        return getattr(obj, attr, None)
    else:
        curr, next_item = attr.split('.', 1)
        return hGetAttr(getattr(obj, curr, None), next_item)


def sortByItem(l, *args, **kwargs):
    """Sort the list ``l``, filled of objects with dict interface by items with key in ``*args``.
    Return the list

    :param l: the list, where items values must be of consistent type
    :param args: a list of keys to sort for. Each key can be reverse sorted by adding ``:d`` to the key.
    :param hkeys: if ``True`` and a key contains ``.``, then it is interpreted as a hierarchical
                  path and sub dict are looked for"""
    def safeCmp(a, b):
        if a is None:
            if b is None:
                return 0
            return -1
        elif b is None:
            return 1
        else:
            return ((a > b) - (a < b))

    def hGetItem(obj, attr):
        if obj is None:
            return None
        curr, next_item = attr.split('.', 1)
        return hGetAttr(obj.get(curr, None), next_item)

    criteria = []
    rev = False
    for crit in list(args):
        caseInsensitive = False
        if ':' in crit:
            crit, direction = crit.split(':', 1)
            if direction.endswith('*'):
                direction = direction[0:-1]
                caseInsensitive = True
            if direction.lower() in ['d', 'desc', 'descending']:
                rev = not rev
        criteria = [(crit, rev, caseInsensitive)] + criteria
    hkeys = kwargs.get('hkeys', False)

    for crit, rev, caseInsensitive in criteria:
        if caseInsensitive:
            if '.' in crit and hkeys:
                cmp_func = lambda a, b: safeCmp((hGetItem(a, crit) or '').lower(), (hGetItem(b, crit) or '').lower())
                l.sort(key=cmp_to_key(cmp_func))
            else:
                cmp_func = lambda a, b: safeCmp((a.get(crit, None) or '').lower(), (b.get(crit, None) or '').lower())
                l.sort(key=cmp_to_key(cmp_func))
        else:
            if '.' in crit and hkeys:
                cmp_func = lambda a, b: safeCmp(hGetItem(a, crit), hGetItem(b, crit))
                l.sort(key=cmp_to_key(cmp_func))
            else:
                cmp_func = lambda a, b: safeCmp(a.get(crit, None), b.get(crit, None))
                l.sort(key=cmp_to_key(cmp_func))
        if rev:
            l.reverse()
    return l


def sortByAttr(l, *args):
    """Sort a list of objects by their attributes.

    :param l: the list of objects to sort
    :param args: attribute names to sort by. Can include ':d' suffix for descending order.
                 Supports hierarchical attributes with dot notation (e.g., 'user.name')
    :return: the sorted list

    Example:
        sortByAttr(objects, 'name')  # sort by name ascending
        sortByAttr(objects, 'age:d')  # sort by age descending
        sortByAttr(objects, 'dept.name', 'salary:d')  # multi-level sort
    """
    criteria = list(args)
    criteria.reverse()
    for crit in criteria:
        rev = None
        if ':' in crit:
            crit, rev = crit.split(':', 1)
        if '.' in crit:
            l.sort(key=lambda i: hGetAttr(i, crit))
        else:
            l.sort(key=lambda i: getattr(i, crit, None))
        if rev:
            l.reverse()
    return l


def merge(*args):
    """Merge multiple iterables into a single list, removing duplicates while preserving order.

    Elements from the first iterable are added first, followed by unique elements from
    subsequent iterables.

    :param args: variable number of iterables to merge
    :return: merged list with unique elements

    Note: Elements must be iterable. No type checking is performed.

    Example:
        merge([1, 2, 3], [2, 3, 4], [4, 5])  # returns [1, 2, 3, 4, 5]
    """
    result = list(args[0])
    for l in args[1:]:
        for el in l:
            if el not in result:
                result.append(el)
    return result


class GnrNamedList(list):
    """A list-like object that allows access to elements by both index and column name.

    This class combines list and dict-like interfaces, enabling both numeric and named
    access to elements. It's primarily used to represent rows from CSV, Excel, or XML files.

    :param index: dict mapping column names (str) to their position indices (int)
    :param values: optional list of initial values ordered according to the index mapping.
                   If None, initializes with None values for all columns.

    Example:
        >>> index = {'name': 0, 'age': 1, 'city': 2}
        >>> row = GnrNamedList(index, ['Alice', 30, 'NYC'])
        >>> row[0]           # Access by numeric index
        'Alice'
        >>> row['name']      # Access by column name
        'Alice'
        >>> row['email'] = 'alice@example.com'  # Add new column dynamically
        >>> 'name' in row    # Check column existence
        True

    Note: Constructor parameters are not type-checked.
    """
    def __init__(self, index, values=None):
        self._index = index
        if values is None:
            self[:] = [None] * len(index)
        else:
            self[:] = values

    def __getitem__(self, x):
        if type(x) == int or type(x) == slice:
            return list.__getitem__(self, x)
        else:
            x = self._index[x]
            try:
                return list.__getitem__(self, x)
            except:
                if x > len(self._index):
                    raise

    def __contains__(self, what):
        return what in self._index

    def __setitem__(self, x, v):
        if type(x) not in (int, slice):
            n = self._index.get(x)
            if n is None:
                n = len(self._index)
                self._index[x] = n
            x = n
        try:
            list.__setitem__(self, x, v)
        except:
            n = len(self._index)
            if x > n:
                raise
            else:
                self.extend([None] * (n - len(self)))
                list.__setitem__(self, x, v)

    def __str__(self):
        return '[%s]' % ','.join(['%s=%s' % (k, v) for k, v in list(self.items())])

    def __repr__(self):
        return '[%s]' % ','.join(['%s=%s' % (k, v) for k, v in list(self.items())])

    def get(self, x, default=None):
        """Get value by column name or index, returning default if not found."""
        try:
            return self[x]
        except:
            return default

    def has_key(self, x):
        """Return True if the key is in the index, False otherwise."""
        return x in self._index

    def items(self):
        """Return (key, value) pairs ordered by column position."""
        items = list(self._index.items())
        result = [None] * len(items)
        for k, v in items:
            result[v] = (k, self[v])
        return result

    def iteritems(self):
        """Yield (key, value) pairs ordered by column position."""
        items = list(self._index.items())
        result = [None] * len(items)
        for k, v in items:
            yield (k, self[v])

    def keys(self):
        """Return column names ordered by position."""
        items = list(self._index.items())
        result = [None] * len(items)
        for k, v in items:
            result[v] = k
        return result

    @deprecated(message='do not use pop in named tuple')
    def pop(self, x, dflt=None):
        """Remove and return value — deprecated, breaks column index mapping."""
        if type(x) != int:
            x = self._index[x]
        try:
            return list.pop(self, x)
        except:
            if x > len(self._index):
                raise

    def update(self, d):
        """Update values from a dict."""
        for k, v in list(d.items()):
            self[k] = v

    def values(self):
        """Return all values as a tuple."""
        return tuple(self[:] + [None] * (len(self._index) - len(self)))

    def extractItems(self, columns):
        """Extract (key, value) pairs for specified columns (or all if None)."""
        if columns:
            return [(k, self[k]) for k in columns]
        else:
            return list(self.items())

    def extractValues(self, columns):
        """Extract values for specified columns (or all if None)."""
        if columns:
            return [self[k] for k in columns]
        else:
            return list(self.values())


_MOVED_TO_FLATFILES = frozenset({
    'XlsReader', 'XlsxReader', 'CsvReader', 'XmlReader',
    'getReader', 'readTab', 'readCSV_new', 'readCSV', 'readXLS',
})


def __getattr__(name):
    if name in _MOVED_TO_FLATFILES:
        warnings.warn(
            f"'{name}' has been moved to gnr.core.flatfiles. "
            f"Import from gnr.core.gnrlist is deprecated.",
            DeprecationWarning,
            stacklevel=2,
        )
        from gnr.core import flatfiles
        return getattr(flatfiles, name)
    raise AttributeError(f"module 'gnr.core.gnrlist' has no attribute {name!r}")
