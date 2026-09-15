# SPDX-License-Identifier: LGPL-2.1-or-later
"""Native-base adaptations of GenroPy compatibility helpers.

Adapted from ``gnr.core.gnrbag`` in GenroPy.
Copyright (c) 2004-2026 Softwell sas/srl and the GenroPy contributors.
"""

from __future__ import annotations

import linecache
import os
import sys

from genro_bag import Bag, BagResolver


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
