"""Tests for issue #1007: site-wide default PDF margins (``sys.pdf_render``)
applied independently of the htmltopdf implementation.

Unit tests cover ``HtmlToPdfService.pageMarginsFromPdfKwargs`` (margin
normalization), ``BagToHtmlWeb.pdfMarginKwargs`` (print-defined margins
suppress the preference margins) and the ``page_margins_defined`` letterhead
flag computed by ``BagToHtml.prepareTemplates``.

The integration tests resolve the real weasyprint implementation from the
repository's ``resources/common`` tree (same harness as
``services_addservice_test``), render real HTML documents and assert the text
position in the produced PDF: preference margins must win over a document
``@page {margin:0}``, an explicit ``pageMargin`` must skip them entirely while
winning over the document itself (#1022), and a document's own ``@page``
margins must survive when no preference is set.
They are skipped when weasyprint or pymupdf are not importable.
"""

import os
from types import SimpleNamespace

import pytest

from gnr.core.gnrbag import Bag
from gnr.core.gnrbaghtml import BagToHtml
from gnr.lib.services import BaseServiceType
from gnr.lib.services.htmltopdf import HtmlToPdfService
from gnr.lib.services.storage import StorageNode, BaseLocalService
from gnr.web.gnrbaseclasses import BagToHtmlWeb
from gnr.web.gnrwsgisite_proxy.gnrresourceloader import ResourceLoader

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
COMMON_RESOURCES = os.path.join(REPO_ROOT, 'resources', 'common')
MM_TO_PT = 72 / 25.4

HTML_TEMPLATE = """<html><head><style>
%s
body { margin: 0; padding: 0; }
div { margin: 0; padding: 0; }
</style></head><body><div>MARKER</div></body></html>"""

DOC_PAGE_MARGIN_ZERO = HTML_TEMPLATE % '@page { size: A4; margin: 0; }'
DOC_PAGE_MARGIN_15MM = HTML_TEMPLATE % '@page { size: A4; margin: 15mm; }'
DOC_NO_PAGE_RULE = HTML_TEMPLATE % ''


# --- HtmlToPdfService.pageMarginsFromPdfKwargs ------------------------------

def test_page_margins_bare_numbers_get_mm():
    """Bare numbers and numeric strings keep wkhtmltopdf's implicit mm unit."""
    service = HtmlToPdfService(parent=None)
    margins = service.pageMarginsFromPdfKwargs(dict(margin_top=10, margin_bottom=12.5,
                margin_left='8', margin_right=' 6.25 '))
    assert margins == dict(top='10mm', bottom='12.5mm', left='8mm', right='6.25mm')


def test_page_margins_zero_is_a_value():
    """A margin of 0 is a defined value, not a missing one: it must survive
    normalization (the print-margin suppression relies on it)."""
    service = HtmlToPdfService(parent=None)
    margins = service.pageMarginsFromPdfKwargs(dict(margin_top=0, margin_left='0'))
    assert margins == dict(top='0mm', left='0mm')


def test_page_margins_explicit_units_preserved():
    service = HtmlToPdfService(parent=None)
    margins = service.pageMarginsFromPdfKwargs(dict(margin_top='1cm', margin_bottom='0.5in',
                margin_left='10px', margin_right='2em'))
    assert margins == dict(top='1cm', bottom='0.5in', left='10px', right='2em')


def test_page_margins_empty_or_missing_skipped():
    service = HtmlToPdfService(parent=None)
    assert service.pageMarginsFromPdfKwargs(dict(margin_top=None, margin_bottom='',
                margin_left='   ')) == {}
    assert service.pageMarginsFromPdfKwargs(dict(margin_top=5)) == dict(top='5mm')
    assert service.pageMarginsFromPdfKwargs({}) == {}
    assert service.pageMarginsFromPdfKwargs(None) == {}


def test_page_margins_input_not_consumed():
    """The raw margin_* keys must stay in pdf_kwargs: the wkhtmltopdf path
    still translates every pdf_kwargs entry to a --margin-* CLI flag."""
    service = HtmlToPdfService(parent=None)
    pdf_kwargs = dict(margin_top=10, margin_left='1cm', zoom=1.2)
    service.pageMarginsFromPdfKwargs(pdf_kwargs)
    assert pdf_kwargs == dict(margin_top=10, margin_left='1cm', zoom=1.2)


def test_page_margins_unrelated_keys_ignored():
    service = HtmlToPdfService(parent=None)
    margins = service.pageMarginsFromPdfKwargs(dict(zoom=1.2, header_html='x'))
    assert margins == {}


def test_page_margins_locale_and_spacing_normalized():
    """Decimal commas become dots and internal whitespace is removed before
    validation ('1,5' typed in an italian locale, '10 mm')."""
    service = HtmlToPdfService(parent=None)
    margins = service.pageMarginsFromPdfKwargs(dict(margin_top='1,5', margin_bottom='10 mm',
                margin_left='1.5 cm'))
    assert margins == dict(top='1.5mm', bottom='10mm', left='1.5cm')


def test_page_margins_invalid_values_skipped():
    """A value that is not a valid css length after normalization must skip the
    side entirely: interpolated verbatim it would be dropped by the renderer,
    making that side silently fall back differently from the others."""
    service = HtmlToPdfService(parent=None)
    assert service.pageMarginsFromPdfKwargs(dict(margin_top='abc', margin_bottom='-5',
                margin_left='10furlongs', margin_right='1..5')) == {}
    assert service.pageMarginsFromPdfKwargs(dict(margin_top=-5)) == {}
    #a valid side survives next to invalid ones
    assert service.pageMarginsFromPdfKwargs(dict(margin_top='abc',
                margin_left=10)) == dict(left='10mm')


# --- BagToHtmlWeb.pdfMarginKwargs -------------------------------------------

def make_bagtohtmlweb(**attrs):
    """A real BagToHtmlWeb skipping the site-bound constructor:
    pdfMarginKwargs only reads the page geometry class attributes."""
    instance = BagToHtmlWeb.__new__(BagToHtmlWeb)
    for name, value in attrs.items():
        setattr(instance, name, value)
    return instance


def test_pdf_margin_kwargs_passthrough_without_print_margins():
    """No margins defined by the print: pdf_kwargs go through untouched and
    the sys.pdf_render preference margins stay applicable."""
    printer = make_bagtohtmlweb()
    assert printer.pdfMarginKwargs(None) == {}
    assert printer.pdfMarginKwargs(dict(zoom=1.2)) == dict(zoom=1.2)


def test_pdf_margin_kwargs_print_margins_force_zero():
    """A print defining its own page margins (inner html offsets) must zero
    the service margins, otherwise the preference margins would add up."""
    printer = make_bagtohtmlweb(page_margin_top=15.0)
    assert printer.pdfMarginKwargs({}) == dict(margin_top=0, margin_bottom=0,
                margin_left=0, margin_right=0)


def test_pdf_margin_kwargs_letterhead_zero_margins_force_zero():
    """A letterhead with margins explicitly set to 0 (edge-to-edge) is a
    defined geometry: the page_margins_defined flag must suppress the
    preference margins even though every page_margin_* is 0."""
    printer = make_bagtohtmlweb(page_margins_defined=True)
    assert printer.pdfMarginKwargs({}) == dict(margin_top=0, margin_bottom=0,
                margin_left=0, margin_right=0)


def test_pdf_margin_kwargs_explicit_override_wins():
    """Explicit htmltopdf_*/pdf_kwargs margins beat the forced zeros."""
    printer = make_bagtohtmlweb(page_margin_top=15.0)
    result = printer.pdfMarginKwargs(dict(margin_top=5))
    assert result == dict(margin_top=5, margin_bottom=0, margin_left=0, margin_right=0)


def test_pdf_margin_kwargs_does_not_mutate_input():
    printer = make_bagtohtmlweb(page_margin_top=15.0)
    pdf_kwargs = dict(zoom=1.2)
    printer.pdfMarginKwargs(pdf_kwargs)
    assert pdf_kwargs == dict(zoom=1.2)


# --- BagToHtml.prepareTemplates: page_margins_defined -----------------------

def letterhead_template(**page_attrs):
    layer = Bag()
    for name, value in page_attrs.items():
        layer['main.page.%s' % name] = value
    template = Bag()
    template['top_layer'] = layer
    return template


def test_page_margins_defined_false_without_letterhead():
    """Without a letterhead the flag stays False, even on a second run after
    prepareTemplates assigned the page_margin_* instance attributes (they must
    not be inspected: it would suppress the preference on every re-run)."""
    printer = BagToHtml(templateLoader=lambda **kwargs: None)
    printer.prepareTemplates()
    assert printer.page_margins_defined is False
    printer.prepareTemplates()
    assert printer.page_margins_defined is False


def test_page_margins_defined_with_letterhead_zero_margins():
    """The letterhead editor seeds every new letterhead with page.* = 0, so a 0
    cannot be told apart from an explicit edge-to-edge choice: any loaded
    letterhead means designer-controlled geometry and sets the flag."""
    printer = BagToHtml(templateLoader=lambda **kwargs: letterhead_template(
                top=0, left=0, right=0, bottom=0))
    printer.prepareTemplates()
    assert printer.page_margins_defined is True
    assert printer.page_margin_top == 0


def test_page_margins_defined_with_letterhead_margins():
    printer = BagToHtml(templateLoader=lambda **kwargs: letterhead_template(top=12))
    printer.prepareTemplates()
    assert printer.page_margins_defined is True
    assert printer.page_margin_top == 12


def test_page_margins_defined_with_letterhead_without_margins():
    """Old letterheads may lack the page.* values entirely: the flag depends on
    the letterhead being loaded, not on its vintage."""
    printer = BagToHtml(templateLoader=lambda **kwargs: letterhead_template())
    printer.prepareTemplates()
    assert printer.page_margins_defined is True


def test_page_margins_defined_reset_on_rerun_without_letterhead():
    """prepareTemplates may run more than once on the same instance: a re-run
    without letterhead must reset the flag even though the first run assigned
    the page_margin_* instance attributes (they must not be inspected)."""
    templates = [letterhead_template(top=12), None]
    printer = BagToHtml(templateLoader=lambda **kwargs: templates.pop(0))
    printer.prepareTemplates()
    assert printer.page_margins_defined is True
    printer.prepareTemplates()
    assert printer.page_margins_defined is False


# --- weasyprint integration --------------------------------------------------

def make_pdf_site(tmp_path):
    """A minimal site facade: a real ResourceLoader over the repo resources
    plus a real local storage service rooted at tmp_path."""
    site = SimpleNamespace(
        site_path=str(tmp_path),
        site_name='htmltopdftest',
        gnr_config=None,
        debug=False,
        getStatic=lambda name: None,
        default_page=None,
    )
    site.resource_loader = ResourceLoader(site)
    site.resources_dirs = [COMMON_RESOURCES]
    storage = BaseLocalService(parent=site, base_path=str(tmp_path))
    storage.service_name = 'temp'
    site.storageNode = lambda path, **kwargs: path if isinstance(path, StorageNode) \
        else StorageNode(parent=site, path=str(path).split(':', 1)[-1], service=storage)
    return site


def marker_origin(tmp_path, html, **write_kwargs):
    """Render html through the real weasyprint service and return the
    (x0, y0) position in points of the MARKER text on the first page."""
    pytest.importorskip('weasyprint')
    fitz = pytest.importorskip('fitz')
    site = make_pdf_site(tmp_path)
    factory = BaseServiceType(site=site, service_type='htmltopdf').getServiceFactory('weasyprint')
    service = factory(site)
    (tmp_path / 'src.html').write_text(html)
    pdf_file = service.writePdf('src.html', None, **write_kwargs)
    try:
        with fitz.open(pdf_file.name) as doc:
            words = doc[0].get_text('words')
    finally:
        pdf_file.close()
        os.unlink(pdf_file.name)
    markers = [word for word in words if word[4] == 'MARKER']
    assert markers, 'marker text not found in the rendered pdf'
    return markers[0][0], markers[0][1]


def test_weasyprint_pref_margins_beat_document_zero_margins(tmp_path):
    """The core of issue #1007: sys.pdf_render margins must be applied even to
    documents declaring @page {margin:0} (every GnrHtmlBuilder print does)."""
    x0, y0 = marker_origin(tmp_path, DOC_PAGE_MARGIN_ZERO,
                pdf_kwargs=dict(margin_top=30, margin_left=20))
    assert x0 >= 20 * MM_TO_PT - 1
    assert y0 >= 30 * MM_TO_PT - 1


def test_weasyprint_no_prefs_keeps_document_zero_margins(tmp_path):
    x0, y0 = marker_origin(tmp_path, DOC_PAGE_MARGIN_ZERO, pdf_kwargs={})
    assert x0 < 5 * MM_TO_PT
    assert y0 < 5 * MM_TO_PT


def test_weasyprint_ua_default_survives_without_prefs_and_page_rule(tmp_path):
    """Without preference margins no stylesheet is appended at all: raw html
    without a @page rule of its own (grid pdf export, pagededitor preview)
    keeps the weasyprint UA default margins instead of going edge-to-edge."""
    x0, y0 = marker_origin(tmp_path, DOC_NO_PAGE_RULE, pdf_kwargs={})
    assert x0 > 50
    assert y0 > 50


def test_weasyprint_partial_prefs_zero_the_missing_sides(tmp_path):
    """Once at least one preference side is set, the missing sides default to 0
    (symmetric, predictable output) instead of the weasyprint UA default."""
    x0, y0 = marker_origin(tmp_path, DOC_NO_PAGE_RULE,
                pdf_kwargs=dict(margin_top=30))
    assert y0 >= 30 * MM_TO_PT - 1
    assert x0 < 5 * MM_TO_PT


def test_weasyprint_document_own_margins_survive_without_prefs(tmp_path):
    """The margin:0 defaults are plain user declarations: a document
    deliberately declaring its own @page margins must keep them."""
    x0, y0 = marker_origin(tmp_path, DOC_PAGE_MARGIN_15MM, pdf_kwargs={})
    assert x0 >= 15 * MM_TO_PT - 1
    assert y0 >= 15 * MM_TO_PT - 1


def test_weasyprint_explicit_pagemargin_wins_and_skips_pref_margins(tmp_path):
    """An explicit pageMargin argument wins over the preference margins: they
    must not be injected at all, and the pageMargin itself must be honoured
    against the document's own @page {margin:0} (#1022). The upper bound keeps
    the preference margins (20mm/30mm) out."""
    x0, y0 = marker_origin(tmp_path, DOC_PAGE_MARGIN_ZERO,
                pageSize='A4', pageMargin='5mm',
                pdf_kwargs=dict(margin_top=30, margin_left=20))
    assert 5 * MM_TO_PT - 1 <= x0 < 8 * MM_TO_PT
    assert 5 * MM_TO_PT - 1 <= y0 < 8 * MM_TO_PT


def test_weasyprint_explicit_pagemargin_beats_document_own_margins(tmp_path):
    """The counterpart of test_weasyprint_document_own_margins_survive_without_prefs:
    a document declaring @page {margin:15mm} keeps it only while nobody asks for
    a margin. An explicit pageMargin is authoritative and shrinks it to 5mm."""
    x0, y0 = marker_origin(tmp_path, DOC_PAGE_MARGIN_15MM,
                pageSize='A4', pageMargin='5mm')
    assert 5 * MM_TO_PT - 1 <= x0 < 8 * MM_TO_PT
    assert 5 * MM_TO_PT - 1 <= y0 < 8 * MM_TO_PT


def test_weasyprint_pref_margins_beat_pagesize_only_zero_margin(tmp_path):
    """A pageSize with no pageMargin still emits margin:0, but as a plain
    declaration: the preference margins carry !important and must survive it,
    exactly as they do when no pageSize is passed at all."""
    x0, y0 = marker_origin(tmp_path, DOC_PAGE_MARGIN_ZERO, pageSize='A4',
                pdf_kwargs=dict(margin_top=30, margin_left=20))
    assert x0 >= 20 * MM_TO_PT - 1
    assert y0 >= 30 * MM_TO_PT - 1


def test_weasyprint_zero_margins_beat_document_margins(tmp_path):
    """margin_*=0 in pdf_kwargs (what pdfMarginKwargs injects for prints
    defining their own margins) must win over the document @page margins."""
    x0, y0 = marker_origin(tmp_path, DOC_PAGE_MARGIN_15MM,
                pdf_kwargs=dict(margin_top=0, margin_bottom=0,
                                margin_left=0, margin_right=0))
    assert x0 < 5 * MM_TO_PT
    assert y0 < 5 * MM_TO_PT
