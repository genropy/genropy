# -*- coding: utf-8 -*-
"""gnrrlab - ReportLab PDF generation resource.

This module provides a base class for generating PDF documents using
ReportLab. It integrates with the Genro page system and storage nodes.

Classes:
    RlabResource: Base class for PDF generation resources.

Note:
    This module depends on the `reportlab` package.
"""

from __future__ import annotations

from io import BytesIO
from typing import TYPE_CHECKING, Any

from reportlab.pdfgen import canvas

from gnr.core.gnrstring import slugify

if TYPE_CHECKING:
    from gnr.web.gnrwebpage import GnrWebPage


class RlabResource:
    """Base class for ReportLab PDF generation resources.

    Provides infrastructure for generating PDF documents with ReportLab,
    integrating with Genro's page system and storage nodes.

    Subclasses should override the :meth:`main` method to implement
    their specific PDF generation logic.

    Args:
        page: The Genro web page instance.
        resource_table: The database table object.
        parent: Optional parent resource.
        **kwargs: Additional keyword arguments.

    Attributes:
        rows_table: Table for row data (class attribute).
        virtual_columns: Virtual columns to include (class attribute).
        pdf_folder: Storage folder for PDFs. Defaults to 'page:pdf'.
        cached: Caching configuration (class attribute).
        client_locale: Whether to use client locale. Defaults to False.
        row_relation: Relation for row data (class attribute).
        subtotal_caption_prefix: Prefix for subtotal captions.

    Example:
        >>> class MyPdfResource(RlabResource):
        ...     def main(self):
        ...         self.canvas.drawString(100, 750, "Hello, World!")
    """

    rows_table: str | None = None
    virtual_columns: list[str] | None = None
    pdf_folder: str = "page:pdf"
    cached: bool | None = None
    client_locale: bool = False
    row_relation: str | None = None
    subtotal_caption_prefix: str = "!![en]Totals"

    def __init__(
        self,
        page: "GnrWebPage | None" = None,
        resource_table: Any | None = None,
        parent: Any | None = None,
        **kwargs: Any,
    ) -> None:
        self.parent = parent
        self.page = page
        self.site = page.site  # type: ignore[union-attr]
        self.db = page.db  # type: ignore[union-attr]
        self.locale = (
            self.page.locale  # type: ignore[union-attr]
            if self.client_locale
            else self.site.server_locale
        )
        self.tblobj = resource_table
        self.maintable = resource_table.fullname if resource_table else None
        self.templateLoader = self.db.table("adm.htmltemplate").getTemplate
        self.thermo_wrapper = self.page.btc.thermo_wrapper  # type: ignore[union-attr]
        self.letterhead_sourcedata: Any = None
        self._gridStructures: dict[str, Any] = {}
        self.record: Any = None
        self.canvas: canvas.Canvas | None = None
        self.pdfSn: Any = None
        self.thermo_kwargs: Any = None
        self.record_idx: int | None = None
        self.language: str | None = None

    def __call__(
        self,
        record: Any | None = None,
        pdf: Any | None = None,
        downloadAs: str | None = None,
        thermo: Any | None = None,
        record_idx: int | None = None,
        resultAs: str | None = None,
        language: str | None = None,
        locale: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Generate PDF for a record.

        Args:
            record: The record to generate PDF for. Use '*' for no record.
            pdf: PDF configuration (unused).
            downloadAs: If set, return PDF as download.
            thermo: Thermo wrapper kwargs.
            record_idx: Index of record in batch processing.
            resultAs: 'url' to return URL, otherwise returns file path.
            language: Language code for localization.
            locale: Locale override.
            **kwargs: Additional arguments passed to makePdf.

        Returns:
            PDF file path, URL, or binary content depending on arguments.
        """
        if not record:
            return None
        self.thermo_kwargs = thermo
        self.record_idx = record_idx
        if record == "*":
            record = None
        else:
            record = self.tblobj.recordAs(record, virtual_columns=self.virtual_columns)
        if locale:
            self.locale = locale  # locale forced
        self.language = language
        if self.language:
            self.language = self.language.lower()
            self.locale = locale or "{language}-{languageUPPER}".format(
                language=self.language, languageUPPER=self.language.upper()
            )
        elif self.locale:
            self.language = self.locale[:2].lower()
        self.makePdf(record=record, **kwargs)

        if downloadAs:
            with self.pdfSn.open("rb") as f:
                self.page.response.add_header(  # type: ignore[union-attr]
                    "Content-Disposition",
                    str("attachment; filename=%s" % self.pdfSn.basename),
                )
                self.page.response.content_type = "application/pdf"  # type: ignore[union-attr]
                result = f.read()
            return result
        else:
            return self.pdfSn.url() if resultAs == "url" else self.pdfSn.fullpath

    def getPdfPath(self, *args: Any, **kwargs: Any) -> str:
        """Get internal path for PDF storage.

        Args:
            *args: Arguments passed to storage node.
            **kwargs: Keyword arguments passed to storage node.

        Returns:
            Internal file system path.

        Note:
            May be overridden in subclasses.
        """
        return self.site.getPdfStorageNode(*args, **kwargs).internal_path

    def getPdfStorageNode(self, *args: Any, **kwargs: Any) -> Any:
        """Get storage node for PDF.

        Args:
            *args: Arguments for storage node path.
            **kwargs: Keyword arguments for storage node.

        Returns:
            Storage node instance.
        """
        return self.site.storageNode(self.pdf_folder, *args, **kwargs)

    def makePdfIO(self, record: Any | None = None, **kwargs: Any) -> bytes:
        """Generate PDF and return as bytes (in-memory).

        Args:
            record: The record to generate PDF for.
            **kwargs: Additional arguments.

        Returns:
            PDF content as bytes.

        Note:
            Sets response headers for inline PDF display.
        """
        pdf = BytesIO()
        self.canvas = canvas.Canvas(pdf)
        self.main()
        self.canvas.showPage()
        self.canvas.save()
        pdf.seek(0)
        self.response.add_header(  # type: ignore[attr-defined]
            "Content-Disposition", str("inline; filename=%s" % "test_pdf.pdf")
        )
        self.response.content_type = "application/pdf"  # type: ignore[attr-defined]
        return pdf.read()

    def outputDocName(self, ext: str = "pdf") -> str:
        """Generate output document filename.

        Args:
            ext: File extension. Defaults to 'pdf'.

        Returns:
            Generated filename based on table and record caption.
        """
        if ext and not ext[0] == ".":
            ext = ".%s" % ext
        caption = ""
        if self.record is not None:
            caption = slugify(self.tblobj.recordCaption(self.record))
            idx = self.record_idx
            if idx is not None:
                caption = "%s_%i" % (caption, idx)
        doc_name = "%s_%s%s" % (self.tblobj.name, caption, ext)
        return doc_name

    def makePdf(self, record: Any | None = None, **kwargs: Any) -> None:
        """Generate PDF to storage node.

        Args:
            record: The record to generate PDF for.
            **kwargs: Additional arguments.
        """
        self.record = record
        self.pdfSn = self.getPdfStorageNode(self.outputDocName())
        with self.pdfSn.local_path() as pdf_path:
            self.canvas = canvas.Canvas(pdf_path)
            self.main()
            self.canvas.showPage()
            self.canvas.save()

    def main(self) -> None:
        """Main PDF generation method.

        Must be overridden in subclasses to implement specific PDF
        generation logic. Use ``self.canvas`` to draw on the PDF.

        Example:
            >>> def main(self):
            ...     self.canvas.drawString(100, 750, "Title")
            ...     self.canvas.drawString(100, 700, "Content...")
        """
        # REVIEW:DEAD — stub method, must be overridden
        pass


__all__ = ["RlabResource"]
