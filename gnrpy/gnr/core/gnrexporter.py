# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package       : GenroPy core - see LICENSE for details
# module gnrexporter : data export to various formats
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
"""Data export utilities for various formats.

This module provides writer classes for exporting data to different formats:
- CSV (tab or custom separator)
- HTML tables
- JSON
- Excel (xlsx or xls depending on openpyxl availability)

Example:
    >>> writer_class = getWriter('csv')
    >>> writer = writer_class(
    ...     columns=['name', 'age'],
    ...     headers=['Name', 'Age'],
    ...     coltypes={'name': 'T', 'age': 'I'},
    ...     filepath='/tmp/export.csv'
    ... )
    >>> writer.writeHeaders()
    >>> writer.writeRow({'name': 'John', 'age': 30})
    >>> writer.workbookSave()
"""

from __future__ import annotations

from typing import TYPE_CHECKING

try:
    import openpyxl  # noqa: F401

    from gnr.core.gnrxls import XlsxWriter as ExcelWriter
except Exception:
    # REVIEW:SMELL - bare except, should be ImportError
    from gnr.core.gnrxls import XlsWriter as ExcelWriter

if TYPE_CHECKING:
    from typing import Any, Iterator
    from pathlib import Path


def getWriter(mode: str) -> type[BaseWriter]:
    """Get the writer class for the specified export format.

    Args:
        mode: Export format ('csv', 'html', 'json', or 'xls').

    Returns:
        Writer class for the specified format.

    Raises:
        KeyError: If mode is not a supported format.

    Example:
        >>> WriterClass = getWriter('csv')
        >>> writer = WriterClass(columns=['col1'], headers=['Col 1'], ...)
    """
    writers: dict[str, type[BaseWriter]] = {
        "csv": CsvWriter,
        "html": HtmlTableWriter,
        "json": JsonWriter,
        "xls": ExcelWriter,  # type: ignore[dict-item]
    }
    return writers[mode]


class BaseWriter:
    """Base class for data export writers.

    Provides common functionality for exporting tabular data to
    various formats. Subclasses implement format-specific behavior.

    Args:
        columns: List of column identifiers.
        coltypes: Dictionary mapping column names to type codes
            ('T'=text, 'I'=integer, 'N'=numeric, etc.).
        headers: List of header labels for display.
        filepath: Output file path (optional, returns string if None).
        locale: Locale for text formatting.
        rowseparator: Separator between rows.
        colseparator: Separator between columns.
        **kwargs: Additional format-specific options.

    Attributes:
        content_type: MIME content type for the output format.
        headers: Column header labels.
        columns: Column identifiers.
        coltypes: Column type mapping.
        filepath: Output file path.
        locale: Formatting locale.
        result: Accumulated output data.
        rowseparator: Row separator string.
        colseparator: Column separator string.
        toText: Text conversion function from gnrstring.
    """

    content_type: str = "text/plain"

    def __init__(
        self,
        columns: list[str] | None = None,
        coltypes: dict[str, str] | None = None,
        headers: list[str] | None = None,
        filepath: str | Path | None = None,
        locale: str | None = None,
        rowseparator: str | None = None,
        colseparator: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the base writer.

        Args:
            columns: List of column identifiers.
            coltypes: Dictionary mapping column names to type codes.
            headers: List of header labels.
            filepath: Output file path.
            locale: Locale for formatting.
            rowseparator: Separator between rows.
            colseparator: Separator between columns.
            **kwargs: Additional options (ignored in base class).
        """
        self.headers = headers or []
        self.columns = columns
        self.coltypes = coltypes
        self.filepath = filepath
        self.locale = locale
        self.result: list[Any] = []
        self.rowseparator = rowseparator
        self.colseparator = colseparator
        from gnr.core.gnrstring import toText

        self.toText = toText

    def cleanCol(self, txt: str, dtype: str | None) -> str:
        """Clean column text for safe export.

        Removes or escapes characters that could cause issues in
        the output format, including potential formula injection.

        Args:
            txt: Text to clean.
            dtype: Column data type code.

        Returns:
            Cleaned text safe for export.
        """
        if self.rowseparator:
            txt = txt.replace(self.rowseparator, " ")
        if self.colseparator:
            txt = txt.replace(self.colseparator, " ")
        txt = (
            txt.replace("\n", " ")
            .replace("\r", " ")
            .replace("\t", " ")
            .replace('"', "'")
        )
        if txt:
            if txt[0] in ("+", "=", "-"):
                # Prevent formula injection in spreadsheets
                txt = " %s" % txt
            elif txt[0].isdigit() and (dtype in ("T", "A", "", None)):
                txt = "%s" % txt  # how to escape numbers in text columns?
        return txt

    def writeHeaders(self, separator: str = "\t", **kwargs: Any) -> None:
        """Write column headers to output.

        Args:
            separator: Column separator (default: tab).
            **kwargs: Additional options.
        """
        pass

    def writeRow(
        self, row: dict[str, Any], separator: str = "\t", **kwargs: Any
    ) -> None:
        """Write a data row to output.

        Args:
            row: Dictionary of column values.
            separator: Column separator (default: tab).
            **kwargs: Additional options.
        """
        pass

    def join(self, data: list[str]) -> str:
        """Join data with row separator.

        Args:
            data: List of strings to join.

        Returns:
            Joined string.
        """
        return self.rowseparator.join(list(data))  # type: ignore[union-attr]

    def workbookSave(self) -> str | None:
        """Save the workbook to file or return as string.

        Returns:
            Result string if no filepath, None if saved to file.
        """
        if not self.filepath:
            return "\n".join(self.result)
        if hasattr(self.filepath, "open"):
            csv_open = self.filepath.open  # type: ignore[union-attr]
        else:
            csv_open = lambda **kw: open(self.filepath, **kw)  # type: ignore[arg-type]
        with csv_open(mode="wb") as f:
            separator = self.rowseparator or "\n"
            result = separator.join(self.result)
            f.write(result.encode("utf-8"))
        return None

    def composeAll(
        self,
        data: list[dict[str, Any]] | None = None,
        filepath: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Compose output from multiple data exports.

        Args:
            data: List of export data dictionaries.
            filepath: Output file path (unused in base).
            **kwargs: Additional options.
        """
        for export_data in data or []:
            self.write(export_data)  # type: ignore[attr-defined]

    def compose(self, data: dict[str, Any]) -> str:
        """Compose a single data export.

        Args:
            data: Export data dictionary.

        Returns:
            Composed output string.

        Raises:
            NotImplementedError: Must be implemented by subclasses.
        """
        raise NotImplementedError

    def setStructInfo(self, struct: dict[str, Any], obj: Any = None) -> None:
        """Set structure information from export metadata.

        Args:
            struct: Structure dictionary with columns, headers, etc.
            obj: Target object (defaults to self).
        """
        obj = obj or self
        for k in ("columns", "headers", "groups", "coltypes", "formats"):
            setattr(obj, k, struct.get(k))


class CsvWriter(BaseWriter):
    """CSV format writer.

    Exports data to CSV format with configurable separators.
    Default separators are newline for rows and tab for columns.

    Attributes:
        extension: File extension ('csv').
    """

    extension: str = "csv"

    def __init__(
        self,
        columns: list[str] | None = None,
        coltypes: dict[str, str] | None = None,
        headers: list[str] | None = None,
        filepath: str | Path | None = None,
        locale: str | None = None,
        rowseparator: str | None = None,
        colseparator: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize CSV writer.

        Args:
            columns: List of column identifiers.
            coltypes: Dictionary mapping column names to type codes.
            headers: List of header labels.
            filepath: Output file path.
            locale: Locale for formatting.
            rowseparator: Row separator (default: newline).
            colseparator: Column separator (default: tab).
            **kwargs: Additional options.
        """
        rowseparator = rowseparator or "\n"
        super().__init__(
            columns=columns,
            coltypes=coltypes,
            headers=headers,
            filepath=filepath,
            locale=locale,
            rowseparator=rowseparator,
            colseparator=colseparator,
            **kwargs,
        )

    def writeHeaders(self, separator: str | None = None, **kwargs: Any) -> None:
        """Write CSV headers.

        Args:
            separator: Column separator override.
            **kwargs: Additional options.
        """
        self.result.append(self.composeHeader(separator=separator, **kwargs))

    def writeRow(
        self, row: dict[str, Any], separator: str | None = None, **kwargs: Any
    ) -> None:
        """Write a CSV data row.

        Args:
            row: Dictionary of column values.
            separator: Column separator override.
            **kwargs: Additional options.
        """
        self.result.append(self.composeRow(row, separator=separator, **kwargs))

    def composeHeader(self, separator: str | None = None, **kwargs: Any) -> str:
        """Compose the header row.

        Args:
            separator: Column separator override.
            **kwargs: Additional options.

        Returns:
            Header row string.
        """
        separator = separator or self.colseparator or "\t"
        return separator.join(self.headers)

    def composeRow(
        self, row: dict[str, Any], separator: str | None = None, **kwargs: Any
    ) -> str:
        """Compose a data row.

        Args:
            row: Dictionary of column values.
            separator: Column separator override.
            **kwargs: Additional options.

        Returns:
            Data row string.
        """
        separator = separator or self.colseparator or "\t"
        return separator.join(
            [
                self.cleanCol(
                    self.toText(row.get(col), locale=self.locale),
                    self.coltypes.get(col, "T"),  # type: ignore[union-attr]
                )
                for col in self.columns or []
            ]
        )

    def composeAll(
        self, data: list[dict[str, Any]] | None = None, **kwargs: Any
    ) -> Iterator[str]:
        """Compose all data as a generator.

        Yields rows one at a time, suitable for streaming output.
        Adds identifier and caption columns if multiple exports.

        Args:
            data: List of export data dictionaries.
            **kwargs: Additional options.

        Yields:
            Composed row strings.
        """
        firstExport = True
        extra_headers: list[str] = []
        extra_columns: list[str] = []
        if not (isinstance(data, list) and len(data) == 1):
            extra_headers = ["Identifier", "Caption"]
            extra_columns = ["_export_identifier", "_export_caption"]
        for export_data in data or []:
            if firstExport:
                struct = export_data["struct"]
                self.headers = extra_headers + struct["headers"]
                self.columns = extra_columns + struct["columns"]
                self.coltypes = struct["coltypes"]
                firstExport = False
                yield self.composeHeader()
            for r in export_data["rows"]:
                r["_export_identifier"] = export_data.get("identifier")
                r["_export_caption"] = export_data.get("name")
                yield self.composeRow(r)


class HtmlTableWriter(BaseWriter):
    """HTML table format writer.

    Exports data as HTML table markup.

    Attributes:
        content_type: MIME type ('text/html').
        extension: File extension ('html').
    """

    content_type: str = "text/html"
    extension: str = "html"

    def __init__(
        self,
        columns: list[str] | None = None,
        coltypes: dict[str, str] | None = None,
        headers: list[str] | None = None,
        filepath: str | Path | None = None,
        locale: str | None = None,
        rowseparator: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize HTML table writer.

        Args:
            columns: List of column identifiers.
            coltypes: Dictionary mapping column names to type codes.
            headers: List of header labels.
            filepath: Output file path.
            locale: Locale for formatting.
            rowseparator: Row separator (default: '<br/>').
            **kwargs: Additional options.
        """
        rowseparator = rowseparator or "<br/>"
        super().__init__(
            columns=columns,
            coltypes=coltypes,
            headers=headers,
            filepath=filepath,
            locale=locale,
            rowseparator=rowseparator,
            **kwargs,
        )
        self.rows: list[str] = []

    def writeHeaders(self, separator: str = "", **kwargs: Any) -> None:
        """Write HTML table headers.

        Args:
            separator: Separator between header cells.
            **kwargs: Additional options.
        """
        self.result.append(self.composeHeaders(separator=separator))

    def writeRow(self, row: dict[str, Any], separator: str = "", **kwargs: Any) -> None:
        """Write an HTML table row.

        Args:
            row: Dictionary of column values.
            separator: Separator between cells.
            **kwargs: Additional options.
        """
        self.rows.append(self.composeRow(row, separator=separator))

    def composeHeaders(self, separator: str = "", **kwargs: Any) -> str:
        """Compose the table header section.

        Args:
            separator: Separator between header cells.
            **kwargs: Additional options.

        Returns:
            HTML thead element string.
        """
        return f"<thead>{separator.join(['<th>%s</th>' % h for h in self.headers])}</thead>"

    def composeRow(
        self, row: dict[str, Any], separator: str = "", **kwargs: Any
    ) -> str:
        """Compose a table row.

        Args:
            row: Dictionary of column values.
            separator: Separator between cells.
            **kwargs: Additional options.

        Returns:
            HTML tr element string.
        """
        return f"<tr>{separator.join(['<td>%s</td>' % self.cleanCol(self.toText(row.get(col), locale=self.locale), self.coltypes[col]) for col in self.columns or []])}</tr>"  # type: ignore[index]

    def workbookSave(self) -> str | None:
        """Save the HTML table to file or return as string.

        Returns:
            HTML table string if no filepath, None if saved to file.
        """
        self.result.append("<tbody>%s</tbody>" % "".join(self.rows))
        result = "<table>%s</table>" % "".join(self.result)
        if not self.filepath:
            return result
        if hasattr(self.filepath, "open"):
            csv_open = self.filepath.open  # type: ignore[union-attr]
        else:
            csv_open = lambda **kw: open(self.filepath, **kw)  # type: ignore[arg-type]
        with csv_open(mode="wb") as f:
            f.write(result.encode("utf-8"))
        return None

    def composeAll(
        self, data: list[dict[str, Any]] | None = None, **kwargs: Any
    ) -> Iterator[str]:
        """Compose all data as a generator.

        Args:
            data: List of export data dictionaries.
            **kwargs: Additional options.

        Yields:
            Composed HTML table strings.
        """
        for export_data in data or []:
            yield self.compose(export_data)

    def compose(self, data: dict[str, Any]) -> str:
        """Compose a single HTML table.

        Args:
            data: Export data dictionary with 'struct', 'name', 'rows'.

        Returns:
            Complete HTML table string.
        """
        self.setStructInfo(data["struct"])
        result = []
        name = data["name"]
        # REVIEW:BUG - typo: 'captipn' instead of 'caption'
        result.append(f'<table class="gnrexport_tbl"><caption>{name}</captipn>')
        result.append(self.composeHeaders())
        result.append("<tbody>")
        for row in data["rows"]:
            result.append(self.composeRow(row))
        result.append("</tbody>")
        result.append("</table>")
        return "".join(result)

    def save(self, storageNode: Any = None) -> None:
        """Save to a storage node.

        Args:
            storageNode: Storage node with open() method.
        """
        with storageNode.open("wb") as f:
            f.write("<br/>".join(self.result))


class JsonWriter(BaseWriter):
    """JSON format writer.

    Exports data as a list of JSON objects.

    Attributes:
        extension: File extension ('json').
    """

    extension: str = "json"

    def writeRow(self, row: dict[str, Any], **kwargs: Any) -> None:
        """Write a JSON object row.

        Args:
            row: Dictionary of column values.
            **kwargs: Additional options.
        """
        self.result.append(
            {
                col: self.cleanCol(
                    self.toText(row.get(col), locale=self.locale),
                    self.coltypes[col],  # type: ignore[index]
                )
                for col in self.columns or []
            }
        )

    def workbookSave(self) -> str | None:
        """Save the JSON data to file or return as string.

        Returns:
            JSON string if no filepath, None if saved to file.
        """
        if not self.filepath:
            return "".join(self.result)  # type: ignore[arg-type]
        if hasattr(self.filepath, "open"):
            csv_open = self.filepath.open  # type: ignore[union-attr]
        else:
            csv_open = lambda **kw: open(self.filepath, **kw)  # type: ignore[arg-type]
        with csv_open(mode="wb") as f:
            result = "".join(self.result)  # type: ignore[arg-type]
            f.write(result.encode("utf-8"))
        return None
