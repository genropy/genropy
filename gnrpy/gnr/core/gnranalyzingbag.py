# -*- coding: utf-8 -*-
"""gnranalyzingbag - Bag subclass for data analysis and aggregation.

This module provides :class:`AnalyzingBag`, a specialized Bag that supports
grouping, aggregation, and analysis of tabular data structures.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from gnr.core.gnrbag import Bag


class AnalyzingBag(Bag):
    """A Bag subclass specialized for data analysis and aggregation.

    Provides methods to analyze collections of records, grouping them
    by specified fields and computing aggregations like sums, averages,
    counts, and distinct values.

    Inherits from :class:`~gnr.core.gnrbag.Bag`.

    Example:
        >>> bag = AnalyzingBag()
        >>> data = [{'category': 'A', 'value': 10}, {'category': 'A', 'value': 20}]
        >>> bag.analyze(data, group_by=['category'], sum=['value'])
    """

    def analyze(
        self,
        data: Iterable[dict[str, Any]],
        group_by: list[str | Callable[[dict[str, Any]], str]] | None = None,
        sum: list[str] | None = None,  # noqa: A002
        collect: list[str] | None = None,
        keep: list[str] | None = None,
        distinct: list[str] | None = None,
        key: str | None = None,
        captionCb: Callable[[Any, dict[str, Any], Any], str] | None = None,
        collectIdx: bool = True,
    ) -> None:
        """Analyze and aggregate data into a hierarchical Bag structure.

        Groups the input data according to ``group_by`` fields and computes
        various aggregations on each group.

        Args:
            data: Iterable of dictionaries (records) to analyze.
            group_by: List of field names or callables to group by.
                If a string starts with '*', uses the literal string as label.
                If a callable, it receives the row and returns a label.
            sum: List of field names to sum within each group.
                Creates ``sum_<field>`` and ``avg_<field>`` attributes.
            collect: List of field names whose values to collect into lists.
                Creates ``collect_<field>`` attribute as a list.
            keep: List of field names to keep (first value encountered).
                Creates ``k_<field>`` attribute.
            distinct: List of field names to count distinct values.
                Creates ``dist_<field>`` (set) and ``count_<field>`` attributes.
            key: Field name to use as unique key. If None, uses row index.
            captionCb: Callback to generate node captions.
                Receives (group, row, bagnode) and returns a string.
            collectIdx: If True, track unique indices in a set (default).
                If False, just increment counter.
        """
        totalize = sum

        def groupLabel(row: dict[str, Any], group: str | Callable) -> str:
            """Extract or compute the group label for a row."""
            if isinstance(group, str):
                if group.startswith("*"):
                    label = group[1:]
                else:
                    label = row[group]
            else:
                label = group(row)
            if label is None:
                return ""
            if not isinstance(label, str):
                label = str(label)
            return label

        def updateTotals(bagnode: Any, k: Any, row: dict[str, Any]) -> None:
            """Update aggregation totals on a bag node."""
            attr = bagnode.getAttr()
            if collectIdx:
                idx = attr.setdefault("idx", set())
                idx.add(k)
                attr["count"] = len(idx)
            else:
                if "count" not in attr:
                    attr["count"] = 0
                attr["count"] += 1
            if totalize is not None:
                for fld in totalize:
                    lbl = "sum_%s" % fld
                    tt = attr[lbl] = attr.get(lbl, 0) + (row.get(fld, 0) or 0)
                    lbl = "avg_%s" % fld
                    attr[lbl] = tt / attr["count"]
            if collect is not None:
                for fld in collect:
                    lbl = "collect_%s" % fld
                    lst = attr.get(lbl, [])
                    lst.append(row[fld])
                    attr[lbl] = lst
            if distinct is not None:
                for fld in distinct:
                    fldset = attr.setdefault("dist_%s" % fld, set())
                    fldset.add(row[fld])
                    attr["count_%s" % fld] = len(fldset)

            if keep is not None:
                for fld in keep:
                    lbl = "k_%s" % fld
                    value = attr.get(lbl, None)
                    if not value:
                        attr[lbl] = row[fld]

        for rowind, row in enumerate(data):
            currbag = self
            for gr in group_by or []:
                label = groupLabel(row, gr)
                label = label.replace(".", "_") or "_"
                bagnode = currbag.getNode(label, autocreate=True)
                if bagnode.value is None:
                    bagnode.setAttr(_pkey=self.nodeCounter)
                    bagnode.value = Bag()
                currbag = bagnode.value
                if key is None:
                    k = rowind
                else:
                    k = row[key]
                updateTotals(bagnode, k, row)
                if captionCb:
                    bagnode.setAttr(caption=captionCb(gr, row, bagnode))
                else:
                    bagnode.setAttr(caption=label)

    @property
    def nodeCounter(self) -> int:
        """Auto-incrementing counter for assigning unique node keys.

        Returns:
            The next unique counter value.
        """
        if not hasattr(self, "_nodeCounter"):
            self._nodeCounter = 0
        self._nodeCounter += 1
        return self._nodeCounter


__all__ = ["AnalyzingBag"]
