"""Print handling utilities using CUPS for network printing.

This module provides classes for managing print jobs through CUPS,
including PDF generation, printer connections, and file conversion.

Note:
    This module appears to be partially obsolete. The NetworkPrintService
    in gnr.lib.services.networkprint provides similar functionality and
    may be the preferred approach.

Dependencies:
    - cups: Python CUPS bindings (optional, gracefully handled if missing)
"""

from __future__ import annotations

import os.path
from typing import TYPE_CHECKING

try:
    import cups

    HAS_CUPS = True
except ImportError:
    cups = None  # type: ignore[assignment]
    HAS_CUPS = False

from gnr.core import logger
from gnr.core.gnrlang import GnrException
from gnr.core.gnrbag import Bag
from gnr.lib.services import GnrBaseService
from gnr.core.gnrdecorator import extract_kwargs

if TYPE_CHECKING:
    from typing import Any


class PrintHandlerError(GnrException):
    """Exception raised for print handling errors."""

    pass


class PrinterConnection(GnrBaseService):
    """Connection to a printer or PDF output.

    Manages printing through CUPS or PDF file generation.
    Supports both direct printing to network printers and
    PDF output with optional zip compression.

    Args:
        parent: Parent PrintHandler instance.
        printer_name: Name of the printer or 'PDF' for PDF output.
        printerParams: Printer configuration parameters.
        **kwargs: Additional configuration options.

    Attributes:
        parent: Parent PrintHandler instance.
        orientation: Page orientation setting.
        printAgent: Method used for printing (printPdf or printCups).
    """

    service_name = "print"

    def __init__(
        self,
        parent: PrintHandler,
        printer_name: str | None = None,
        printerParams: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize printer connection.

        Args:
            parent: Parent PrintHandler instance.
            printer_name: Name of the printer or 'PDF' for PDF output.
            printerParams: Printer configuration parameters.
            **kwargs: Additional configuration options.
        """
        self.parent = parent
        printerParams = printerParams or {}
        self.orientation = printerParams.pop("orientation", None)
        if printer_name == "PDF":
            self.initPdf(printerParams=printerParams, **kwargs)
        else:
            self.initPrinter(printer_name, printerParams, **kwargs)

    def initPdf(
        self, printerParams: dict[str, Any] | None = None, **kwargs: Any
    ) -> None:
        """Initialize PDF output mode.

        Args:
            printerParams: Configuration including 'zipped' option.
            **kwargs: Additional options (ignored).
        """
        printerParams = printerParams or dict()
        self.zipped = printerParams.pop("zipped", None)
        self.printAgent = self.printPdf

    def printPdf(
        self,
        pdf_list: list[str],
        jobname: str,
        outputFilePath: str | None = None,
    ) -> str:
        """Output PDFs to a file.

        Either joins PDFs into a single file or creates a zip archive.

        Args:
            pdf_list: List of PDF file paths.
            jobname: Name of the print job (unused for PDF output).
            outputFilePath: Base path for output file (extension added).

        Returns:
            Base filename of the created output file.
        """
        if self.zipped:
            outputFilePath += ".zip"  # type: ignore[operator]
            self.parent.zipPdf(pdf_list, outputFilePath)
        else:
            outputFilePath += ".pdf"  # type: ignore[operator]
            self.parent.joinPdf(pdf_list, outputFilePath)
        return os.path.basename(outputFilePath)  # type: ignore[arg-type]

    def printCups(self, pdf_list: list[str], jobname: str, **kwargs: Any) -> None:
        """Print PDFs through CUPS.

        Args:
            pdf_list: List of PDF file paths to print.
            jobname: Name of the print job.
            **kwargs: Additional options (ignored).
        """
        self.cups_connection.printFiles(
            self.printer_name, pdf_list, jobname, self.printer_options
        )

    def initPrinter(
        self,
        printer_name: str | None = None,
        printerParams: Bag | dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize CUPS printer connection.

        Args:
            printer_name: Name of the CUPS printer.
            printerParams: Printer options including paper, tray, source.
            **kwargs: Additional options (ignored).
        """
        printerParams = printerParams or Bag()
        self.cups_connection = cups.Connection()  # type: ignore[union-attr]
        self.printer_name = printer_name
        printer_media = []
        for media_option in ("paper", "tray", "source"):
            media_value = printerParams["printer_options"] and printerParams[
                "printer_options"
            ].pop(media_option)
            if media_value:
                printer_media.append(media_value)
        self.printer_options = printerParams["printer_options"] or {}
        if printer_media:
            self.printer_options["media"] = str(",".join(printer_media))
        self.printAgent = self.printCups

    def printFiles(
        self,
        file_list: list[str],
        jobname: str = "GenroPrint",
        storeFolder: str | None = None,
        outputFilePath: str | None = None,
    ) -> str | None:
        """Print or output files.

        Converts HTML files to PDF if needed, then prints or outputs.

        Args:
            file_list: List of file paths to print.
            jobname: Name of the print job.
            storeFolder: Folder for temporary PDF storage.
            outputFilePath: Output path for PDF mode.

        Returns:
            Output filename for PDF mode, None for CUPS printing.
        """
        pdf_list = self.parent.autoConvertFiles(
            file_list, storeFolder, orientation=self.orientation
        )
        return self.printAgent(pdf_list, jobname, outputFilePath=outputFilePath)


class PrintHandler:
    """Handler for print operations.

    Provides methods for printer discovery, PDF conversion, and
    managing print connections. Supports both CUPS printing and
    PDF file output.

    Note:
        Consider using NetworkPrintService from gnr.lib.services.networkprint
        for new implementations.

    Args:
        parent: Parent object providing services (site or application).

    Attributes:
        hasCups: Whether CUPS is available.
        parent: Parent service provider.
        paper_size: Dictionary of supported paper sizes.
        paper_tray: Dictionary of supported paper trays.
    """

    # REVIEW:SMELL - These dicts are duplicated in NetworkPrintService
    paper_size: dict[str, str] = {
        "A4": "!!A4",
        "Legal": "!!Legal",
        "A4Small": "!!A4 with margins",
        "COM10": "!!COM10",
        "DL": "!!DL",
        "Letter": "!!Letter",
        "ISOB5": "ISOB5",
        "JISB5": "JISB5",
        "LetterSmall": "LetterSmall",
        "LegalSmall": "LegalSmall",
    }
    paper_tray: dict[str, str] = {
        "MultiPurpose": "!!MultiPurpose",
        "Transparency": "!!Transparency",
        "Upper": "!!Upper",
        "Lower": "!!Lower",
        "LargeCapacity": "!!LargeCapacity",
    }

    def __init__(self, parent: Any = None) -> None:
        """Initialize print handler.

        Args:
            parent: Parent object providing services.
        """
        global HAS_CUPS
        self.hasCups = HAS_CUPS
        self.parent = parent

    @extract_kwargs(pdf=True)
    def htmlToPdf(
        self,
        srcPath: str,
        destPath: str,
        orientation: str | None = None,
        page_height: int | None = None,
        page_width: int | None = None,
        pdf_kwargs: dict[str, Any] | None = None,
        htmlTemplate: str | None = None,
        bodyStyle: str | None = None,
    ) -> str:
        """Convert HTML file to PDF.

        Args:
            srcPath: Path to source HTML file.
            destPath: Destination path for PDF.
            orientation: Page orientation ('portrait' or 'landscape').
            page_height: Custom page height.
            page_width: Custom page width.
            pdf_kwargs: Additional PDF conversion options.
            htmlTemplate: HTML template to use.
            bodyStyle: CSS body style to apply.

        Returns:
            Path to the created PDF file.
        """
        return self.parent.getService("htmltopdf").htmlToPdf(
            srcPath,
            destPath,
            orientation=orientation,
            page_height=page_height,
            page_width=page_width,
            pdf_kwargs=pdf_kwargs,
            htmlTemplate=htmlTemplate,
            bodyStyle=bodyStyle,
        )

    def autoConvertFiles(
        self,
        files: list[str],
        storeFolder: str | None,
        orientation: str | None = None,
    ) -> list[str]:
        """Convert files to PDF format as needed.

        HTML files are converted to PDF; PDF files pass through unchanged.

        Args:
            files: List of file paths to process.
            storeFolder: Folder for storing converted PDFs.
            orientation: Page orientation for conversion.

        Returns:
            List of PDF file paths.

        Raises:
            PrintHandlerError: If a file is neither HTML nor PDF.
        """
        resultList = []
        for filename in files:
            baseName, ext = os.path.splitext(os.path.basename(filename))
            if ext.lower() == ".html":
                resultList.append(
                    self.htmlToPdf(filename, storeFolder, orientation=orientation)
                )
            elif ext.lower() == ".pdf":
                resultList.append(filename)
            else:
                raise PrintHandlerError("not pdf file")
        return resultList

    def getPrinters(self) -> Bag:
        """Get available printers from CUPS.

        Returns:
            Bag containing printer information organized by location.
        """
        printersBag = Bag()
        if self.hasCups:
            cups_connection = cups.Connection()  # type: ignore[union-attr]
            for printer_name, printer in list(cups_connection.getPrinters().items()):
                printer.update(dict(name=printer_name))
                printersBag.setItem(
                    "%s.%s"
                    % (printer["printer-location"], printer_name.replace(":", "_")),
                    None,
                    printer,
                )
        else:
            logger.error("pyCups is not installed")
        return printersBag

    def getPrinterAttributes(self, printer_name: str) -> Bag:
        """Get attributes for a specific printer.

        Args:
            printer_name: Name of the CUPS printer.

        Returns:
            Bag containing supported paper sizes and trays.
        """
        cups_connection = cups.Connection()  # type: ignore[union-attr]
        printer_attributes = cups_connection.getPrinterAttributes(printer_name)
        attributesBag = Bag()
        for i, (media, description) in enumerate(self.paper_size.items()):
            if media in printer_attributes["media-supported"]:
                attributesBag.setItem(
                    "paper_supported.%i" % i, None, id=media, caption=description
                )
        for i, (tray, description) in enumerate(self.paper_tray.items()):
            if tray in printer_attributes["media-supported"]:
                attributesBag.setItem(
                    "tray_supported.%i" % i, None, id=tray, caption=description
                )
        return attributesBag

    def getPrinterConnection(
        self,
        printer_name: str | None = None,
        printerParams: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> PrinterConnection:
        """Create a printer connection.

        Args:
            printer_name: Name of printer or 'PDF' for file output.
            printerParams: Printer configuration.
            **kwargs: Additional options.

        Returns:
            PrinterConnection configured for the specified printer.
        """
        return PrinterConnection(
            self,
            printer_name=printer_name,
            printerParams=printerParams or dict(),
            **kwargs,
        )

    def joinPdf(self, pdf_list: list[str], output_filepath: str) -> None:
        """Join multiple PDFs into a single file.

        Args:
            pdf_list: List of PDF file paths.
            output_filepath: Path for the combined output.
        """
        self.parent.getService("pdf").joinPdf(pdf_list, output_filepath)

    def zipPdf(
        self, file_list: list[str] | None = None, zipPath: str | None = None
    ) -> None:
        """Create a zip archive of PDF files.

        Args:
            file_list: List of file paths to include.
            zipPath: Path for the output zip file.
        """
        self.parent.zipFiles(file_list=file_list, zipPath=zipPath)
