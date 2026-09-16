# SPDX-License-Identifier: LGPL-2.1-or-later
"""Native-base adaptations of GenroPy compatibility helpers.

Adapted from ``gnr.core.gnrbag`` in GenroPy.
Copyright (c) 2004-2026 Softwell sas/srl and the GenroPy contributors.
"""

from __future__ import annotations

import linecache
import os
import sys
import warnings

from genro_bag import Bag, BagResolver


def legacy_walk(self, callback, _mode='static', **kwargs):
    """Bridge the legacy callback-only walk API to native for_each."""
    warnings.warn('Bag.walk is deprecated; use for_each(..., deep=True)',
                  DeprecationWarning, stacklevel=2)

    def invoke(node, **context):
        # Legacy tracking lists describe ancestors, excluding the current node.
        for key in ('_pathlist', '_indexlist'):
            if key in context:
                context[key] = context[key][:-1]
        return callback(node, **context)

    return self.for_each(invoke, static='static' in (_mode or ''), deep=True, **kwargs)


def install_resolver_serialization_bridge():
    """Honor legacy resolver overrides while callers migrate to serialize()."""
    if getattr(BagResolver.serialize, '__genropy_legacy_bridge__', False):
        return
    native_serialize = BagResolver.serialize
    legacy_base = BagResolver.resolverSerialize

    def serialize(self):
        legacy_override = type(self).resolverSerialize
        if legacy_override is legacy_base:
            return native_serialize(self)
        warnings.warn(
            f"{type(self).__name__}.resolverSerialize() is deprecated for TYTX; "
            "move the serialization override to serialize()",
            DeprecationWarning,
            stacklevel=2,
        )
        # The legacy base builds its record directly, without calling serialize(),
        # so overrides using super().resolverSerialize() do not recurse.
        result = dict(legacy_override(self))
        result['resolver_module'] = result.pop('resolvermodule')
        result['resolver_class'] = result.pop('resolverclass')
        return result

    serialize.__genropy_legacy_bridge__ = True
    BagResolver.serialize = serialize


class _GenroPyReference(str):
    """A catalog reference that must bypass localization."""


def _catalog_reference(value, catalog):
    value_type = catalog.getType(value)
    if value_type == "RPC" and not hasattr(value, "__self__"):
        from gnr.core.gnrlang import serializedFuncName
        return _GenroPyReference(serializedFuncName(value, cls=type(value)) + "::RPC")
    if value_type in ("RPC", "CLS"):
        return _GenroPyReference(catalog.asTypedText(value))
    return value


def genropy_reference_rows(rows, catalog):
    """Convert GenroPy callable and class references in flattened Bag rows."""
    excluded = None
    for parent, label, tag, value, attr in rows:
        path = f"{parent}.{label}" if parent else label
        if excluded is not None:
            if parent == excluded or parent.startswith(excluded + "."):
                continue
            excluded = None
        if "__forbidden__" in attr:
            excluded = path
            continue
        yield (
            parent,
            label,
            tag,
            _catalog_reference(value, catalog),
            {key: _catalog_reference(item, catalog) for key, item in attr.items()
             if not callable(item) or isinstance(item, type)
             or hasattr(item, "is_rpc") or hasattr(item, "__safe__")
             or getattr(item, "__name__", "").startswith("rpc_")},
        )


def translated_genropy_rows(rows, translator, branch_markers):
    """Apply legacy scalar-string localization without changing source rows."""
    for parent, label, tag, value, attr in rows:
        if isinstance(value, _GenroPyReference):
            value = str(value)
        elif (translator is not None and isinstance(value, str)
              and value != "::NN" and not value.startswith("::RSLV:")
              and value not in branch_markers):
            value = translator(value)
        attr = {
            key: (str(item) if isinstance(item, _GenroPyReference)
                  else translator(item)
                  if (translator is not None and isinstance(item, str)
                      and not item.startswith("::RSLV:"))
                  else item)
            for key, item in attr.items()
        }
        yield (parent, label, tag, value, attr)


def to_genropy_js(self, translator=None):
    """Return GenroPy-compatible typed rows ready for TYTX encoding."""
    from gnr.core.gnrclasses import GnrClassCatalog
    from genro_tytx import TYPE_REGISTRY

    rows = self._node_flattener()
    rows = genropy_reference_rows(rows, GnrClassCatalog())
    branch_markers = {
        f"::{value_type.__tytx_suffix__}"
        for value_type in TYPE_REGISTRY
        if hasattr(value_type, "__tytx_suffix__")
    }
    rows = translated_genropy_rows(rows, translator, branch_markers)
    return {"rows": list(rows)}


class TraceBackResolver(BagResolver):
    classKwargs = {"cacheTime": 0, "limit": None}
    classArgs = []

    def load(self):
        result = Bag()
        limit = self.limit
        if limit is None:
            limit = getattr(sys, "tracebacklimit", None)
        count = 0
        traceback = sys.exc_info()[2]
        while traceback is not None and (limit is None or count < limit):
            frame = traceback.tb_frame
            line_number = traceback.tb_lineno
            code = frame.f_code
            linecache.checkcache(code.co_filename)
            line = linecache.getline(code.co_filename, line_number).strip() or None
            entry = Bag()
            entry["module"] = os.path.basename(os.path.splitext(code.co_filename)[0])
            entry["filename"] = code.co_filename
            entry["lineno"] = line_number
            entry["name"] = code.co_name
            entry["line"] = line
            entry["locals"] = Bag(
                {name: str(value) for name, value in frame.f_locals.items()}
            )
            result[f"{entry['module']} method: {code.co_name} line: {line_number}"] = (
                entry
            )
            traceback = traceback.tb_next
            count += 1
        return result


class NetBag(BagResolver):
    classKwargs = {"cacheTime": 300, "readOnly": True}
    classArgs = ["url", "method"]

    def init(self):
        import requests
        from gnr.core.gnrclasses import GnrClassCatalog

        self.requests = requests
        self.converter = GnrClassCatalog()

    def load(self):
        try:
            declared = set(self.class_args) | set(self.class_kwargs)
            params = {
                key: self.converter.asTypedText(value)
                for key, value in self._kw.items()
                if key not in declared
            }
            response = self.requests.post(f"{self.url}/{self.method}", data=params)
            return Bag(response.text)
        except Exception as error:
            return Bag({"error": str(error)})
