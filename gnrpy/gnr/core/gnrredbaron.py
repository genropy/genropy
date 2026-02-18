# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy core - see LICENSE for details
# module gnrredbaron : Python source code analysis using RedBaron
# Copyright (c) : 2004 - 2007 Softwell sas - Milano
# Written by    : Giovanni Porcari, Michele Bertoldi
#                 Saverio Porcari, Francesco Porcari, Francesco Cavazzana
# --------------------------------------------------------------------------
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA
"""gnrredbaron - Python source code analysis using RedBaron.

This module provides utilities for analyzing Python source code using the
RedBaron library. It can parse Python files and convert their structure
to a Bag tree representation.

Note:
    Requires the ``redbaron`` package to be installed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

try:
    from redbaron import RedBaron
except Exception:
    RedBaron = False  # type: ignore[misc, assignment]

from gnr.core.gnrbag import Bag

if TYPE_CHECKING:
    from redbaron import RedBaron as RedBaronType


class GnrRedBaron:
    """Python source code analyzer using RedBaron.

    Parses Python source files and provides methods to convert the AST
    structure into a Bag tree representation.

    Args:
        module: Path to the Python module file to analyze.

    Raises:
        Exception: If the redbaron package is not installed.

    Attributes:
        module: Path to the analyzed module.
        redbaron: The RedBaron AST instance.
        child_types: Dictionary of node types to include in tree conversion.

    Example:
        >>> rb = GnrRedBaron('/path/to/module.py')
        >>> tree = rb.toTreeBag()
    """

    child_types: dict[str, bool] = {"class": True}

    def __init__(self, module: str | None = None) -> None:
        self.module = module
        if not RedBaron:
            raise Exception("Missing redbaron")  # noqa: TRY002
        with open(module, "r") as f:  # type: ignore[arg-type]
            self.redbaron: RedBaronType = RedBaron(f.read())

    def toTreeBag(self, node: Any | None = None) -> Bag:
        """Convert the AST to a Bag tree structure.

        Args:
            node: The AST node to convert. If None, uses the root redbaron node.

        Returns:
            A Bag containing the tree structure of the AST.
        """
        # REVIEW:SMELL — method does not return the result Bag
        node = node or self.redbaron
        result = Bag()
        for n in node:
            if n.type in self.child_types:
                result.setItem(n.name, None, caption=n.name, _type=n.type)
        return result  # REVIEW:BUG — added missing return statement

    def moduleToTree(self, module: str) -> None:
        """Convert a module to tree structure.

        Args:
            module: Path to the module.

        Note:
            This method is not yet implemented.
        """
        # REVIEW:DEAD — stub method, not implemented
        pass

    def getModuleElement(self, module: str, element: str | None = None) -> None:
        """Get a specific element from a module.

        Args:
            module: Path to the module.
            element: Name of the element to retrieve.

        Note:
            This method is not yet implemented.
        """
        # REVIEW:DEAD — stub method, not implemented
        pass

    def saveModuleElement(self, module: str, element: str | None = None) -> None:
        """Save a module element.

        Args:
            module: Path to the module.
            element: Name of the element to save.

        Note:
            This method is not yet implemented.
        """
        # REVIEW:DEAD — stub method, not implemented
        pass


__all__ = ["GnrRedBaron"]


# REVIEW:DEAD — __main__ block with hardcoded path, likely for testing only
if __name__ == "__main__":
    rb = GnrRedBaron(
        "/Users/fporcari/sviluppo/genro//Users/fporcari/sviluppo/genro"
        "/resources/common/th/th_view.py"
    )
