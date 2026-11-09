#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Render one source document through several htmltopdf engines and diff them.

Genropy resolves its ``htmltopdf`` service from ``resources/common/services``,
where ``weasyprint`` and ``wk`` (wkhtmltopdf) are two interchangeable
implementations of the same :class:`HtmlToPdfService` contract. They do not
produce the same pdf out of the same html, and this module is the harness that
measures the gap on real prints: it renders a source through every available
implementation, compares each rendering against a reference one with
:mod:`gnr.utils.pdfcompare`, and writes a browsable report.

The engines are optional at runtime: ``weasyprint`` may not be installed and
``wkhtmltopdf`` is an external binary, so :func:`availableImplementations`
reports what can actually run and the harness skips the rest instead of
failing.
"""

import os
import shutil
from html import escape

from gnr.core.gnrlang import GnrException
from gnr.lib.services import BaseServiceType
from gnr.utils import logger
from gnr.utils.pdfcompare import comparePdf, pageOverlay, pageTransform


class HtmlToPdfDiffError(GnrException):
    pass


#the reference implementation every other one is compared against: weasyprint is
#the current default of HtmlToPdfService.conf_htmltopdf
DEFAULT_REFERENCE = 'weasyprint'
DEFAULT_IMPLEMENTATIONS = ('weasyprint', 'wk')


def implementationIsAvailable(implementation):
    """True when an htmltopdf implementation can actually render here.

    :param implementation: the service implementation name (``weasyprint``, ``wk``)"""
    if implementation == 'weasyprint':
        try:
            import weasyprint  # noqa: F401
        except ImportError:
            return False
        return True
    if implementation == 'wk':
        return bool(shutil.which('wkhtmltopdf'))
    return True


def availableImplementations(implementations=DEFAULT_IMPLEMENTATIONS):
    """The subset of implementations that can render on this machine.

    :param implementations: the names to check
    :returns: a tuple of names"""
    return tuple(name for name in implementations if implementationIsAvailable(name))


class HtmlToPdfEngineRunner:
    """Renders the same source html through several htmltopdf implementations.

    :param site: the site (or site facade) the services are bound to: it must
                 expose ``storageNode`` and the resource loader the service
                 factories are resolved through
    :param implementations: the implementation names to render with"""

    def __init__(self, site, implementations=DEFAULT_IMPLEMENTATIONS):
        self.site = site
        self.implementations = tuple(implementations)
        self._services = {}

    def service(self, implementation):
        """The htmltopdf service instance of an implementation, resolved once.

        :param implementation: the service implementation name"""
        if implementation not in self._services:
            factory = BaseServiceType(site=self.site,
                                      service_type='htmltopdf').getServiceFactory(implementation)
            self._services[implementation] = factory(self.site)
        return self._services[implementation]

    def render(self, srcPath, destPath, implementation, pdf_kwargs=None, **kwargs):
        """Render one source document with one implementation.

        ``pdf_kwargs`` and ``stylesheets`` are copied per call: the wkhtmltopdf
        service writes its ``orientation`` and ``quiet`` entries into the dict
        it receives and the weasyprint one appends to the stylesheet list, so a
        shared mutable would leak the first engine's settings into the second
        and quietly compare two different requests.

        :param srcPath: the source html, as a path or a storage node
        :param destPath: where the pdf is written
        :param implementation: the service implementation name
        :param pdf_kwargs: the ``pdf_kwargs`` both services accept
        :returns: the path of the written pdf"""
        kwargs = dict(kwargs)
        if 'stylesheets' in kwargs:
            kwargs['stylesheets'] = list(kwargs['stylesheets'] or [])
        return self.service(implementation).writePdf(srcPath, destPath,
                                                     pdf_kwargs=dict(pdf_kwargs or {}),
                                                     **kwargs)

    def localPath(self, path):
        """Resolve what a service wrote to a path on the local filesystem.

        The services return a storage path (``temp:out/print.pdf``), while the
        geometric comparison reads the files with pymupdf and needs a real
        file. The destination of a comparison run is therefore expected to live
        on a local storage service, which is what a test run or a report run
        uses; a remote destination is rejected here rather than failing later
        with an opaque "no such file".

        :param path: what the service returned, or the requested destination
        :returns: the local filesystem path of the written pdf"""
        node = self.site.storageNode(path)
        local = getattr(node, 'internal_path', None)
        if not local or not os.path.isfile(str(local)):
            raise HtmlToPdfDiffError(
                'the htmltopdf comparison needs a local destination folder, '
                'got %s' % path)
        return str(local)

    def renderAll(self, srcPath, destFolder, basename=None, **kwargs):
        """Render one source document with every requested implementation.

        An implementation that is not installed is skipped, and one that raises
        while rendering is reported as a failure instead of aborting the run:
        on a report over dozens of prints, one engine choking on one print must
        not cost the comparison of all the others.

        :param srcPath: the source html, as a path or a storage node
        :param destFolder: the folder the pdf files are written to
        :param basename: base name of the written files, defaulting to the
                         source file name
        :returns: ``(rendered, failed)``, a dict of implementation to the local
                  path of the written pdf and a dict of implementation to error
                  message"""
        basename = basename or os.path.splitext(os.path.basename(str(srcPath)))[0]
        rendered = {}
        failed = {}
        for implementation in self.implementations:
            if not implementationIsAvailable(implementation):
                continue
            destPath = os.path.join(str(destFolder), '%s_%s.pdf' % (basename, implementation))
            try:
                written = self.render(srcPath, destPath, implementation, **kwargs)
            except Exception as error:
                logger.warning('htmltopdf %s failed on %s: %s', implementation, srcPath, error)
                failed[implementation] = '%s: %s' % (error.__class__.__name__, error)
                continue
            rendered[implementation] = self.localPath(written or destPath)
        return rendered, failed


class EngineComparisonResult:
    """The outcome of comparing one source document across the engines.

    :param name: the name identifying the source in the report
    :param source: the source html path
    :param rendered: dict of implementation to rendered pdf path
    :param failed: dict of implementation to error message
    :param comparisons: dict of implementation to
                        :class:`gnr.utils.pdfcompare.PdfComparison` against the
                        reference rendering"""

    def __init__(self, name, source, reference, rendered=None, failed=None, comparisons=None):
        self.name = name
        self.source = source
        self.reference = reference
        self.rendered = rendered or {}
        self.failed = failed or {}
        self.comparisons = comparisons or {}
        self.overlays = {}

    @property
    def comparable(self):
        """True when the reference and at least one other engine both rendered."""
        return bool(self.comparisons)

    @property
    def identical(self):
        """True when every engine agrees with the reference rendering."""
        return self.comparable and all(comparison.identical
                                       for comparison in self.comparisons.values())

    def describe(self):
        """A multi line human readable summary of this source document."""
        lines = ['## %s' % self.name]
        for implementation, message in sorted(self.failed.items()):
            lines.append('%s: render failed, %s' % (implementation, message))
        if not self.comparable and not self.failed:
            lines.append('nothing to compare: only the reference engine rendered')
        for implementation, comparison in sorted(self.comparisons.items()):
            lines.append(comparison.describe())
        return '\n'.join(lines)


def compareEngines(site, srcPath, destFolder, name=None, reference=DEFAULT_REFERENCE,
                   implementations=DEFAULT_IMPLEMENTATIONS, overlay_dpi=None, **kwargs):
    """Render one source document with every engine and compare them.

    :param site: the site (or site facade) the services are bound to
    :param srcPath: the source html, as a path or a storage node
    :param destFolder: the storage folder the pdf files are written to; it must
                       resolve to a local one, since the comparison reads the
                       written files back
    :param name: the name identifying the source in the report, defaulting to
                 the source file name
    :param reference: the implementation every other one is compared against
    :param implementations: the implementation names to render with
    :param overlay_dpi: when set, also write a false-color overlay png per page,
                        aligned on the fitted transform so only the differences
                        the offset and the zoom do not explain stand out
    :returns: an :class:`EngineComparisonResult`"""
    name = name or os.path.splitext(os.path.basename(str(srcPath)))[0]
    runner = HtmlToPdfEngineRunner(site, implementations=implementations)
    rendered, failed = runner.renderAll(srcPath, destFolder, basename=name, **kwargs)
    result = EngineComparisonResult(name=name, source=str(srcPath), reference=reference,
                                    rendered=rendered, failed=failed)
    if reference not in rendered:
        return result
    for implementation, pdf_path in rendered.items():
        if implementation == reference:
            continue
        comparison = comparePdf(rendered[reference], pdf_path,
                                left_label=reference, right_label=implementation)
        result.comparisons[implementation] = comparison
        if overlay_dpi:
            #next to the rendered pdf files: destFolder is a storage path, while the
            #overlays are written with pymupdf and need a local folder
            result.overlays[implementation] = writeOverlays(
                rendered[reference], pdf_path, comparison,
                os.path.dirname(rendered[reference]),
                '%s_%s' % (name, implementation), dpi=overlay_dpi)
    return result


def writeOverlays(reference_pdf, other_pdf, comparison, destFolder, basename, dpi=100):
    """Write one false-color overlay png per compared page.

    The overlay is aligned on the transform fitted for that page, so a print
    whose only problem is a margin offset comes out black and white and a print
    the engines really disagree on lights up. The unaligned overlay would be
    useless here: a three millimeter shift makes every glyph on the page
    mismatch.

    :param reference_pdf: the reference rendering
    :param other_pdf: the rendering under comparison
    :param comparison: the :class:`gnr.utils.pdfcompare.PdfComparison` of the two
    :param destFolder: the folder the png files are written to
    :param basename: base name of the written files
    :param dpi: rasterization resolution
    :returns: the list of written png paths"""
    paths = []
    for page in comparison.pages:
        pixmap = pageOverlay(reference_pdf, other_pdf, index=page.index, dpi=dpi,
                             transform=pageTransform(page))
        path = os.path.join(str(destFolder), '%s_p%02i.png' % (basename, page.index + 1))
        pixmap.save(path)
        paths.append(path)
    return paths


def compareEnginesOnFolder(site, srcFolder, destFolder, pattern='.html',
                           reference=DEFAULT_REFERENCE,
                           implementations=DEFAULT_IMPLEMENTATIONS,
                           overlay_dpi=None, **kwargs):
    """Compare every source document of a folder across the engines.

    This is the entry point a print regression suite calls: point it at a
    folder of html prints exported from a real application and it renders and
    measures all of them.

    :param srcFolder: the folder holding the source html documents
    :param destFolder: the folder the pdf files (and overlays) are written to
    :param pattern: the file name suffix identifying a source document
    :returns: the list of :class:`EngineComparisonResult`, sorted by name"""
    results = []
    for filename in sorted(os.listdir(str(srcFolder))):
        if not filename.endswith(pattern):
            continue
        results.append(compareEngines(site, os.path.join(str(srcFolder), filename),
                                      destFolder, reference=reference,
                                      implementations=implementations,
                                      overlay_dpi=overlay_dpi, **kwargs))
    return results


REPORT_STYLE = """body{font-family:Arial,sans-serif;font-size:13px;margin:20px;color:#222}
h1{font-size:20px}h2{font-size:15px;margin:18px 0 4px}
table{border-collapse:collapse;margin:8px 0}
td,th{border:1px solid #ccc;padding:3px 8px;text-align:left}
th{background:#eee}
.ok{color:#127a12}.ko{color:#b00}
img{border:1px solid #ccc;max-width:420px;vertical-align:top;margin:4px}
.note{color:#666}"""


def _reportRows(comparison):
    """The per-page table rows of one engine comparison, as html."""
    rows = []
    for page in comparison.pages:
        rows.append('<tr><td>%i</td><td>%+.2f</td><td>%+.2f</td><td>%.4f</td>'
                    '<td>%.4f</td><td>%.2f</td><td class="%s">%s</td></tr>'
                    % (page.index + 1, page.offset_mm[0], page.offset_mm[1],
                       page.scale[0], page.scale[1], page.residual_pt,
                       'ok' if page.identical else 'ko',
                       'identical' if page.identical
                       else escape(page.describe().split(': ', 1)[1])))
    return '\n'.join(rows)


def writeHtmlReport(results, destFolder, filename='index.html',
                    title='htmltopdf engine comparison'):
    """Write a browsable report of a batch of engine comparisons.

    Each source document gets its measured offset, scale and residual per page,
    plus the aligned overlay images when they were produced. The offset and the
    scale say how the engines are configured apart; the residual says whether
    aligning them would be enough.

    :param results: the :class:`EngineComparisonResult` list to report
    :param destFolder: the folder the report is written to
    :param filename: the report file name
    :param title: the report title
    :returns: the path of the written report"""
    parts = ['<html><head><meta charset="utf-8"><title>%s</title><style>%s</style></head><body>'
             % (escape(title), REPORT_STYLE), '<h1>%s</h1>' % escape(title)]
    differing = [result for result in results if result.comparable and not result.identical]
    parts.append('<p>%i documents, %i with differences, %i not comparable.</p>'
                 % (len(results), len(differing),
                    len([result for result in results if not result.comparable])))
    for result in results:
        #print names and engine error messages are data, not markup: a source
        #file named with an ampersand must not break the report it appears in
        parts.append('<h2>%s</h2>' % escape(result.name))
        for implementation, message in sorted(result.failed.items()):
            parts.append('<p class="ko">%s: render failed, %s</p>'
                         % (escape(implementation), escape(message)))
        if not result.comparable:
            if not result.failed:
                parts.append('<p class="note">not comparable: '
                             'the reference engine did not render.</p>')
            continue
        for implementation, comparison in sorted(result.comparisons.items()):
            parts.append('<p>%s vs <b>%s</b>%s</p>'
                         % (escape(comparison.left_label), escape(implementation),
                            '' if comparison.same_page_count
                            else ' &mdash; <span class="ko">page count %i vs %i</span>'
                            % (comparison.left.page_count, comparison.right.page_count)))
            parts.append('<table><tr><th>page</th><th>offset x (mm)</th><th>offset y (mm)</th>'
                         '<th>scale x</th><th>scale y</th><th>residual (pt)</th>'
                         '<th>verdict</th></tr>%s</table>' % _reportRows(comparison))
            for overlay in result.overlays.get(implementation, []):
                parts.append('<img src="%s">' % os.path.basename(overlay))
    parts.append('</body></html>')
    path = os.path.join(str(destFolder), filename)
    with open(path, 'w') as report:
        report.write('\n'.join(parts))
    return path
