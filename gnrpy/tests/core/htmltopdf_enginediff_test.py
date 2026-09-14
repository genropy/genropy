"""Tests for the weasyprint / wkhtmltopdf print comparison harness.

Genropy renders prints through two interchangeable ``htmltopdf``
implementations and they have never agreed. This module tests the
infrastructure that measures the disagreement:
:mod:`gnr.utils.pdfcompare` (pdf geometry and the ``offset``/``scale``
transform fitted between two renderings) and :mod:`gnr.utils.htmltopdfdiff`
(rendering one source through every engine and reporting the differences).

The measuring engine is tested on synthetic pdf documents built with pymupdf,
where every coordinate is known: a harness that mismeasures would otherwise
make every print comparison meaningless.

The engine tests then render real documents through the real services resolved
from ``resources/common/services`` and assert the divergences the harness
exists to track. They assert direction and order of magnitude, not exact
figures: those depend on the installed wkhtmltopdf and weasyprint versions,
while the divergences themselves are structural. They are skipped when an
engine is not installed.
"""

import os

import pymupdf
import pytest

from core.pdfsite import make_pdf_site
from gnr.core.gnrhtml import GnrHtmlBuilder
from gnr.utils.htmltopdfdiff import (DEFAULT_REFERENCE, HtmlToPdfEngineRunner,
                                     availableImplementations, compareEngines,
                                     compareEnginesOnFolder, implementationIsAvailable,
                                     writeHtmlReport)
from gnr.utils.pdfcompare import (MM_TO_PT, comparePdf, fitAxis, matchWords,
                                  pageInkDiffRatio, pageOverlay, pageTransform,
                                  pdfGeometry)

A4_WIDTH = 595.276
A4_HEIGHT = 841.89

#a folder of real application prints (html) to compare, opted in from the
#environment: pointing it at the print_debug folder of an Erpy or Genromed
#instance (sys.pdf_render.keep_html saves every rendered print there) runs the
#whole comparison over that application's prints
FIXTURES_ENV = 'GNR_PRINT_FIXTURES'

BOTH_ENGINES = pytest.mark.skipif(
    len(availableImplementations()) < 2,
    reason='needs both weasyprint and wkhtmltopdf installed')


# --- synthetic pdf helpers ---------------------------------------------------

def write_pdf(path, pages, width=A4_WIDTH, height=A4_HEIGHT, background=None, fontsize=10):
    """Build a pdf with text at known positions.

    :param path: where the pdf is written
    :param pages: one list of ``(text, x, y)`` per page, y being the baseline
    :param background: optional ``(rect, color)`` fill drawn under every page
    :param fontsize: the text size; scaling it together with the positions is
                     what makes a synthetic document a true uniform scaling of
                     another one, since the measured word boxes are anchored on
                     the glyph tops and not on the baselines
    :returns: the path"""
    document = pymupdf.open()
    for page_words in pages:
        page = document.new_page(width=width, height=height)
        if background:
            rect, color = background
            page.draw_rect(pymupdf.Rect(*rect), color=None, fill=color)
        for text, x, y in page_words:
            page.insert_text((x, y), text, fontsize=fontsize)
    document.save(str(path))
    document.close()
    return str(path)


def transformed(words, scale=1.0, offset=(0.0, 0.0)):
    """The same words moved by ``position * scale + offset``."""
    return [(text, x * scale + offset[0], y * scale + offset[1]) for text, x, y in words]


WORDS = [('Alpha', 60.0, 100.0), ('Beta', 300.0, 100.0),
         ('Gamma', 60.0, 400.0), ('Delta', 300.0, 700.0)]


# --- pdf geometry ------------------------------------------------------------

def test_geometry_reads_pages_words_and_page_size(tmp_path):
    path = write_pdf(tmp_path / 'two.pdf', [WORDS, [('Solo', 100.0, 100.0)]])
    geometry = pdfGeometry(path)
    assert geometry.page_count == 2
    assert [word.text for word in geometry.pages[0].words] == ['Alpha', 'Beta', 'Gamma', 'Delta']
    assert geometry.pages[1].text == 'Solo'
    assert round(geometry.pages[0].width) == round(A4_WIDTH)
    assert round(geometry.pages[0].height) == round(A4_HEIGHT)


def test_ink_bbox_wraps_the_content(tmp_path):
    path = write_pdf(tmp_path / 'ink.pdf', [WORDS])
    x0, y0, x1, y1 = pdfGeometry(path).pages[0].ink_bbox
    #the bbox starts at the leftmost glyph and ends after the lowest baseline
    assert 59 <= x0 <= 61
    assert y0 < 100 and y1 > 700
    assert x1 > 300


def test_margins_measure_the_distance_to_the_content(tmp_path):
    path = write_pdf(tmp_path / 'margins.pdf', [[('Alpha', 100.0, 200.0)]])
    page = pdfGeometry(path).pages[0]
    assert abs(page.margins['left'] - 100.0) < 1.0
    assert abs(page.margins['right'] - (page.width - page.ink_bbox[2])) < 0.01
    assert abs(page.margins_mm['left'] - 100.0 / MM_TO_PT) < 0.05


def test_white_background_is_not_content(tmp_path):
    """wkhtmltopdf paints the whole printable area white before drawing.

    Counting that rectangle as ink would make the ink bounding box of every
    wkhtmltopdf page equal to its margin box, hiding the very difference this
    harness measures."""
    path = write_pdf(tmp_path / 'white.pdf', [[('Alpha', 100.0, 200.0)]],
                     background=((10, 10, A4_WIDTH - 10, A4_HEIGHT - 10), (1, 1, 1)))
    page = pdfGeometry(path).pages[0]
    assert page.margins['left'] > 90


def test_visible_background_is_content(tmp_path):
    """The counterpart: a gray band is real ink and must widen the bbox."""
    path = write_pdf(tmp_path / 'gray.pdf', [[('Alpha', 100.0, 200.0)]],
                     background=((10, 10, A4_WIDTH - 10, 60), (0.8, 0.8, 0.8)))
    page = pdfGeometry(path).pages[0]
    assert abs(page.margins['left'] - 10.0) < 1.0
    assert abs(page.margins['top'] - 10.0) < 1.0


def test_blank_page_has_no_ink_and_no_margins(tmp_path):
    path = write_pdf(tmp_path / 'blank.pdf', [[]])
    page = pdfGeometry(path).pages[0]
    assert page.ink_bbox is None
    assert page.margins == {}


# --- the fitted transform ----------------------------------------------------

def test_fit_axis_pure_offset():
    fit = fitAxis([(10.0, 20.0), (100.0, 110.0), (400.0, 410.0)])
    assert abs(fit.scale - 1.0) < 1e-9
    assert abs(fit.offset - 10.0) < 1e-9
    assert fit.residual < 1e-9
    assert fit.samples == 3


def test_fit_axis_scale_and_offset():
    fit = fitAxis([(0.0, 5.0), (100.0, 85.0), (200.0, 165.0)])
    assert abs(fit.scale - 0.8) < 1e-9
    assert abs(fit.offset - 5.0) < 1e-9
    assert fit.residual < 1e-9


def test_fit_axis_reports_what_it_cannot_explain():
    """The residual is what makes the harness useful: a difference a single
    offset and zoom cannot account for is a layout difference, and no margin
    setting will reconcile the two engines."""
    fit = fitAxis([(0.0, 0.0), (100.0, 100.0), (200.0, 230.0)])
    assert fit.residual > 5.0


def test_fit_axis_single_coordinate_pins_the_scale():
    """Any scale fits a single point: inferring one from it would be noise."""
    fit = fitAxis([(100.0, 130.0), (100.0, 130.0)])
    assert fit.scale == 1.0
    assert abs(fit.offset - 30.0) < 1e-9


def test_fit_axis_without_samples():
    fit = fitAxis([])
    assert (fit.scale, fit.offset, fit.samples) == (1.0, 0.0, 0)


def test_match_words_skips_what_only_one_side_has():
    """A word present on one side only must not shift every following pair:
    the fit would inherit the shift and report a translation that is not there."""
    left = pdfGeometryWords([('Alpha', 10, 10), ('Beta', 20, 20), ('Gamma', 30, 30)])
    right = pdfGeometryWords([('Alpha', 10, 10), ('Extra', 15, 15),
                              ('Beta', 20, 20), ('Gamma', 30, 30)])
    pairs = matchWords(left, right)
    assert [(pair[0].text, pair[1].text) for pair in pairs] == [
        ('Alpha', 'Alpha'), ('Beta', 'Beta'), ('Gamma', 'Gamma')]


def pdfGeometryWords(items):
    """Build :class:`Word` instances without going through a pdf."""
    from gnr.utils.pdfcompare import Word
    return [Word(text=text, x0=x, y0=y, x1=x + 10, y1=y + 10) for text, x, y in items]


# --- comparing two renderings ------------------------------------------------

def test_identical_renderings_compare_equal(tmp_path):
    left = write_pdf(tmp_path / 'a.pdf', [WORDS])
    right = write_pdf(tmp_path / 'b.pdf', [WORDS])
    comparison = comparePdf(left, right)
    assert comparison.identical
    assert comparison.pages[0].describe().endswith('identical')
    assert comparison.max_offset_mm < 0.01
    assert comparison.max_residual_pt < 0.01


def test_comparison_detects_a_uniform_offset(tmp_path):
    """The wkhtmltopdf margin problem in its pure form."""
    left = write_pdf(tmp_path / 'a.pdf', [WORDS])
    right = write_pdf(tmp_path / 'b.pdf', [transformed(WORDS, offset=(10.0, 20.0))])
    page = comparePdf(left, right).pages[0]
    assert page.has_offset
    assert not page.has_scale
    assert not page.has_residual
    assert abs(page.offset_pt[0] - 10.0) < 0.5
    assert abs(page.offset_pt[1] - 20.0) < 0.5
    assert abs(page.margin_delta['left'] - 10.0) < 0.5
    assert abs(page.margin_delta['top'] - 20.0) < 0.5
    assert not page.identical


def test_comparison_detects_a_uniform_scale(tmp_path):
    """The other wkhtmltopdf divergence: the whole print shrunk by a factor."""
    left = write_pdf(tmp_path / 'a.pdf', [WORDS])
    right = write_pdf(tmp_path / 'b.pdf', [transformed(WORDS, scale=0.8)], fontsize=8)
    page = comparePdf(left, right).pages[0]
    assert page.has_scale
    assert abs(page.scale[0] - 0.8) < 0.01
    assert abs(page.scale[1] - 0.8) < 0.01
    assert not page.has_residual


def test_comparison_separates_scale_from_offset(tmp_path):
    left = write_pdf(tmp_path / 'a.pdf', [WORDS])
    right = write_pdf(tmp_path / 'b.pdf', [transformed(WORDS, scale=0.9, offset=(12.0, 7.0))],
                      fontsize=9)
    page = comparePdf(left, right).pages[0]
    assert abs(page.scale[0] - 0.9) < 0.01
    assert abs(page.offset_pt[0] - 12.0) < 0.5
    assert abs(page.offset_pt[1] - 7.0) < 0.5
    assert not page.has_residual


def test_comparison_reports_a_layout_difference_as_residual(tmp_path):
    """One block moved on its own: no global offset or zoom explains it."""
    moved = list(WORDS)
    moved[2] = ('Gamma', 200.0, 500.0)
    left = write_pdf(tmp_path / 'a.pdf', [WORDS])
    right = write_pdf(tmp_path / 'b.pdf', [moved])
    page = comparePdf(left, right).pages[0]
    assert page.has_residual
    assert page.residual_pt > 10.0
    assert 'residual' in page.describe()


def test_comparison_reports_a_page_count_mismatch(tmp_path):
    left = write_pdf(tmp_path / 'a.pdf', [WORDS, WORDS])
    right = write_pdf(tmp_path / 'b.pdf', [WORDS])
    comparison = comparePdf(left, right)
    assert not comparison.same_page_count
    assert not comparison.identical
    #the page both documents have is still measured: a pagination difference
    #must not hide the margin difference that probably caused it
    assert len(comparison.pages) == 1
    assert 'page count differs' in comparison.describe()


def test_comparison_reports_missing_text(tmp_path):
    left = write_pdf(tmp_path / 'a.pdf', [WORDS])
    right = write_pdf(tmp_path / 'b.pdf', [WORDS[:-1]])
    page = comparePdf(left, right).pages[0]
    assert not page.same_text
    assert [word.text for word in page.unmatched_left] == ['Delta']
    assert page.unmatched_right == []


def test_comparison_reports_a_page_size_difference(tmp_path):
    left = write_pdf(tmp_path / 'a.pdf', [WORDS])
    right = write_pdf(tmp_path / 'b.pdf', [WORDS], width=A4_WIDTH + 20)
    page = comparePdf(left, right).pages[0]
    assert not page.same_page_size
    assert abs(page.page_size_delta[0] - 20.0) < 0.01


# --- the raster comparison ---------------------------------------------------

def test_aligning_on_the_transform_cancels_a_pure_offset(tmp_path):
    """A print whose only problem is an offset differs on almost every pixel
    until it is realigned: the raw ratio answers "did anything move", the
    aligned one answers "is anything actually different"."""
    left = write_pdf(tmp_path / 'a.pdf', [WORDS])
    right = write_pdf(tmp_path / 'b.pdf', [transformed(WORDS, offset=(20.0, 30.0))])
    page = comparePdf(left, right).pages[0]
    raw = pageInkDiffRatio(left, right, dpi=72)
    aligned = pageInkDiffRatio(left, right, dpi=72, transform=pageTransform(page))
    assert raw > 0.0
    assert aligned < raw / 4


def test_overlay_has_the_reference_page_size(tmp_path):
    left = write_pdf(tmp_path / 'a.pdf', [WORDS])
    right = write_pdf(tmp_path / 'b.pdf', [transformed(WORDS, offset=(20.0, 30.0))])
    page = comparePdf(left, right).pages[0]
    overlay = pageOverlay(left, right, dpi=72, transform=pageTransform(page))
    assert overlay.n == 3
    assert abs(overlay.width - A4_WIDTH) <= 2
    assert abs(overlay.height - A4_HEIGHT) <= 2


# --- the engine harness ------------------------------------------------------

def test_availability_is_reported_not_assumed():
    """The harness must run where an engine is missing: wkhtmltopdf is an
    external binary and weasyprint an optional import."""
    available = availableImplementations()
    assert set(available) <= set(('weasyprint', 'wk'))
    assert implementationIsAvailable('weasyprint') == ('weasyprint' in available)


def write_source(tmp_path, name, body, page_css='@page{size:A4;margin:0}'):
    """Write a source html document in the site storage root."""
    html = """<html><head><meta charset="utf-8"><style>%s
        body{margin:0;padding:0;font-family:Arial,sans-serif;font-size:12px}
        div{margin:0;padding:0}</style></head><body>%s</body></html>""" % (page_css, body)
    (tmp_path / name).write_text(html)
    return name


SPREAD_BODY = ''.join('<div style="position:absolute;top:%imm;left:10mm">Line %02i</div>'
                      % (10 + index * 12, index) for index in range(20))


@BOTH_ENGINES
def test_wkhtmltopdf_indents_a_zero_margin_document(tmp_path):
    """The reported symptom: on a document declaring ``@page {margin:0}``
    weasyprint starts at the page corner and wkhtmltopdf a few millimeters in."""
    source = write_source(tmp_path, 'zero.html', '<div>MARKER</div>')
    result = compareEngines(make_pdf_site(tmp_path), source, 'out', name='zero')
    assert set(result.rendered) == set(('weasyprint', 'wk'))
    page = result.comparisons['wk'].pages[0]
    assert page.left.margins_mm['top'] < 1.0
    assert page.left.margins_mm['left'] < 1.0
    assert page.right.margins_mm['top'] > 1.0
    assert page.right.margins_mm['left'] > 1.0
    assert not result.identical


@BOTH_ENGINES
def test_equal_margins_align_the_engines_horizontally(tmp_path):
    """Feeding both services the same ``margin_*`` removes the horizontal
    offset, which is what makes the margin the actionable part of the gap."""
    source = write_source(tmp_path, 'spread.html', SPREAD_BODY)
    site = make_pdf_site(tmp_path)
    default = compareEngines(site, source, 'out', name='default')
    zeroed = compareEngines(site, source, 'out', name='zeroed',
                            pdf_kwargs=dict(margin_top=0, margin_bottom=0,
                                            margin_left=0, margin_right=0))
    assert default.comparisons['wk'].pages[0].has_offset
    assert abs(zeroed.comparisons['wk'].pages[0].offset_mm[0]) < \
        abs(default.comparisons['wk'].pages[0].offset_mm[0])


@BOTH_ENGINES
def test_wkhtmltopdf_scales_a_genropy_layout_print_down(tmp_path):
    """A real print built by GnrHtmlBuilder, whose layout is positioned in
    absolute millimeters: wkhtmltopdf renders it visibly smaller than
    weasyprint, a divergence no margin setting accounts for, and the fit
    explains it as a uniform zoom rather than as a layout difference."""
    builder = GnrHtmlBuilder(page_width=210, page_height=297, page_margin_top=10,
                             page_margin_left=10, page_margin_right=10,
                             page_margin_bottom=10)
    builder.initializeSrc()
    builder.styleForLayout()
    layout = builder.body.layout(name='main', um='mm', top=0, left=0, width=190,
                                 height=277, border_width=.3, lbl_height=4)
    for index in range(20):
        row = layout.row(height=13)
        row.cell('Row %02i label' % index, width=60, lbl='lbl%02i' % index)
        row.cell('value %i' % index)
    builder.toHtml(str(tmp_path / 'layout.html'))
    result = compareEngines(make_pdf_site(tmp_path), 'layout.html', 'out', name='layout')
    page = result.comparisons['wk'].pages[0]
    assert page.has_scale
    assert page.scale[0] < 0.95
    assert abs(page.scale[0] - page.scale[1]) < 0.01
    #a uniform zoom, not a reflow: the fit accounts for every word
    assert not page.has_residual


@BOTH_ENGINES
def test_engine_comparison_writes_overlays_and_a_report(tmp_path):
    source = write_source(tmp_path, 'spread.html', SPREAD_BODY)
    result = compareEngines(make_pdf_site(tmp_path), source, 'out', name='spread',
                            overlay_dpi=72)
    overlays = result.overlays['wk']
    assert len(overlays) == len(result.comparisons['wk'].pages)
    assert all(os.path.isfile(path) for path in overlays)
    report = writeHtmlReport([result], os.path.dirname(overlays[0]))
    content = open(report).read()
    assert 'spread' in content
    assert os.path.basename(overlays[0]) in content


@BOTH_ENGINES
def test_folder_comparison_covers_every_document(tmp_path):
    source_folder = tmp_path / 'src'
    source_folder.mkdir()
    for name in ('one', 'two'):
        (source_folder / ('%s.html' % name)).write_text(
            '<html><body><div>%s</div></body></html>' % name.upper())
    site = make_pdf_site(tmp_path)
    (tmp_path / 'out').mkdir()
    results = compareEnginesOnFolder(site, str(source_folder), 'out')
    assert [result.name for result in results] == ['one', 'two']
    assert all(result.comparable for result in results)


@BOTH_ENGINES
def test_a_failing_engine_does_not_abort_the_run(tmp_path):
    """One engine choking on one print must not cost the comparison of all the
    others: on a report over dozens of prints that is the difference between a
    partial answer and none."""
    runner = HtmlToPdfEngineRunner(make_pdf_site(tmp_path))
    rendered, failed = runner.renderAll('missing.html', 'out', basename='missing')
    assert rendered == {}
    assert set(failed) == set(('weasyprint', 'wk'))


def test_reference_engine_is_the_service_default():
    """The comparison is stated against weasyprint, the implementation
    HtmlToPdfService falls back to when it is importable."""
    assert DEFAULT_REFERENCE == 'weasyprint'


# --- real application prints -------------------------------------------------

@BOTH_ENGINES
@pytest.mark.skipif(not os.environ.get(FIXTURES_ENV),
                    reason='set %s to a folder of html prints to compare' % FIXTURES_ENV)
def test_application_prints_are_comparable(tmp_path):
    """Run the whole comparison over a real application's prints.

    Point ``GNR_PRINT_FIXTURES`` at a folder of html prints (the ``print_debug``
    folder an instance fills when ``sys.pdf_render.keep_html`` is on) to measure
    that application's prints. The test asserts only that every print is
    renderable and comparable: the differences themselves are the report's
    subject, not a pass or fail, since a difference is what is being
    investigated."""
    source_folder = os.environ[FIXTURES_ENV]
    site = make_pdf_site(tmp_path)
    (tmp_path / 'out').mkdir()
    results = compareEnginesOnFolder(site, source_folder, 'out', overlay_dpi=100)
    assert results, 'no html print found in %s' % source_folder
    report = writeHtmlReport(results, str(tmp_path / 'out'))
    print('\nprint comparison report: %s\n%s' % (
        report, '\n'.join(result.describe() for result in results)))
    assert not [result for result in results if result.failed]
