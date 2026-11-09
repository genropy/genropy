"""Tests for :mod:`gnr.utils.printgeometry`, the page geometry of a print.

A print resource declares its page as class attributes, and the two htmltopdf
engines read those millimeters very differently: weasyprint prints on the
declared page, wkhtmltopdf on its own sheet with the layout shrunk into it. The
module under test reads the declarations out of a project's resources and
resolves them the way ``BagToHtml.prepareTemplates`` does, so that a migration
off wkhtmltopdf can be reasoned about per print instead of per exported file.

The scanner is tested against print modules written to a temporary resource
tree, since what it has to get right is exactly what a real one looks like: a
class inheriting the geometry from another class of the same module, a class
that is not a print at all, a declaration that is not a literal. The probe
document is then rendered through the real weasyprint service and measured, so
that a probe which does not carry the geometry it claims fails here rather than
silently skewing every print comparison built on it.
"""

import os

import pytest

from core.pdfsite import make_pdf_site
from gnr.lib.services import BaseServiceType
from gnr.utils.printgeometry import (PAPER_FORMATS, PrintGeometry,
                                     probeDocument, scanPrintResources)

MM_TO_PT = 72 / 25.4


# --- PrintGeometry resolution ------------------------------------------------

def test_canvas_defaults_to_the_page_format():
    """A print declaring nothing prints on A4, BagToHtml's default format."""
    assert PrintGeometry('p').canvas == PAPER_FORMATS['A4']
    assert PrintGeometry('p', page_format='A5').canvas == PAPER_FORMATS['A5']


def test_canvas_completes_a_single_declared_side_from_the_format():
    """page_width alone keeps the format's other side, as prepareTemplates does."""
    assert PrintGeometry('p', page_width=215).canvas == (215.0, 297.0)
    assert PrintGeometry('p', page_height=292).canvas == (210.0, 292.0)


def test_orientation_is_deduced_from_the_declared_sides():
    """No page_orientation: the taller side wins, exactly as prepareTemplates."""
    assert PrintGeometry('p', page_width=198, page_height=287).orientation == 'V'
    assert PrintGeometry('p', page_width=292, page_height=198).orientation == 'H'


def test_declared_orientation_orders_the_sides():
    """page_orientation is authoritative: it reorders the declared sides rather
    than being deduced from them, which is what makes a print declaring
    297x210 with 'V' come out upright."""
    assert PrintGeometry('p', page_width=297, page_height=210,
                         page_orientation='V').canvas == (210.0, 297.0)
    assert PrintGeometry('p', page_width=198, page_height=287,
                         page_orientation='H').canvas == (287.0, 198.0)


def test_declares_page_size_distinguishes_a_default_from_a_choice():
    assert PrintGeometry('p').declares_page_size is False
    assert PrintGeometry('p', page_format='A5').declares_page_size is False
    assert PrintGeometry('p', page_width=215).declares_page_size is True


# --- what each engine makes of it --------------------------------------------

def test_wk_prints_a_non_paper_canvas_on_plain_a4():
    """The divergence the migration is about: the declared canvas is the sheet
    for weasyprint and nothing at all for wkhtmltopdf."""
    geometry = PrintGeometry('p', page_width=215, page_height=292)
    assert geometry.canvas == (215.0, 292.0)
    assert geometry.wk_paper == (210.0, 297.0)
    assert geometry.wk_orientation == 'Portrait'


def test_wk_paper_turns_with_a_landscape_canvas():
    geometry = PrintGeometry('p', page_width=292, page_height=198)
    assert geometry.wk_orientation == 'Landscape'
    assert geometry.wk_paper == (297.0, 210.0)


def test_standard_paper_flags_the_canvases_that_are_not_sheets():
    assert PrintGeometry('p').standard_paper is True
    assert PrintGeometry('p', page_width=297, page_height=210).standard_paper is True
    assert PrintGeometry('p', page_width=215, page_height=292).standard_paper is False
    assert PrintGeometry('p', page_width=292, page_height=198).standard_paper is False


def test_wk_scale_leaves_a_canvas_that_fits_at_the_binary_shrink():
    """While the layout fits the printable width, the only term left is the
    binary's own constant: on an official patched build, which does not shrink,
    the print comes out at the size it declares."""
    assert PrintGeometry('p', page_width=180, page_height=297).wkScale() == 1.0
    assert PrintGeometry('p', page_width=190, page_height=297).wkScale() == 1.0
    assert PrintGeometry('p', page_width=180, page_height=297).wkScale(shrink=0.77) == 0.77


def test_wk_scale_fits_an_overflowing_canvas_to_the_printable_width():
    geometry = PrintGeometry('p', page_width=300, page_height=400)
    scale = geometry.wkScale()
    assert scale < 1.0
    #the canvas ends up exactly as wide as the printable area of the sheet
    assert abs(300 * scale - (210 - 20)) < 0.01


def test_wk_scale_follows_the_canvas_and_not_only_the_installation():
    """The same binary draws two prints at two different scales, which is why
    one configured factor per instance cannot describe them: the fit term
    belongs to the print."""
    scales = [PrintGeometry('p', page_width=width, page_height=297).wkScale()
              for width in (180, 215, 250, 292)]
    assert scales == sorted(scales, reverse=True)
    assert len(set(scales)) == len(scales)


def test_wk_scale_takes_the_smaller_of_the_two_terms():
    """Neither term alone describes the rendering: a stock Qt build shrinking
    by 0.77 draws a narrow print at 0.77 and a wide one at the fit, whichever
    is smaller."""
    narrow = PrintGeometry('p', page_width=200, page_height=297)
    wide = PrintGeometry('p', page_width=292, page_height=297)
    assert narrow.wkScale(shrink=0.77) == 0.77
    assert abs(wide.wkScale(shrink=0.77) - (210 - 20) / 292) < 1e-9


# --- scanning a project's print resources ------------------------------------

PRINT_MODULE = """from gnr.web.gnrbaseclasses import TableScriptToHtml


class Main(TableScriptToHtml):
    page_width = 215
    page_height = 292
    doc_header_height = 20
"""

INHERITING_MODULE = """from gnr.web.gnrbaseclasses import TableScriptToHtml


class Base(TableScriptToHtml):
    page_width = 292
    page_height = 198
    page_orientation = 'H'


class Main(Base):
    doc_header_height = 10


class Helper(object):
    page_width = 999
"""

COMPUTED_MODULE = """from gnr.web.gnrbaseclasses import TableScriptToHtml

SIDE = 215


class Main(TableScriptToHtml):
    page_width = SIDE
    templates = 'fattura'
"""


def write_resources(tmp_path, modules, table='fattura', package='erpy_fatt'):
    """Write print modules into a resource tree shaped like a real one."""
    folder = tmp_path / package / 'resources' / 'tables' / table / 'html_res'
    folder.mkdir(parents=True)
    for name, source in modules.items():
        (folder / ('%s.py' % name)).write_text(source)
    return str(tmp_path)


def test_scan_reads_the_declared_geometry(tmp_path):
    root = write_resources(tmp_path, {'distinta': PRINT_MODULE})
    geometries = scanPrintResources(root)
    assert len(geometries) == 1
    geometry = geometries[0]
    assert geometry.name == 'erpy_fatt/resources/tables/fattura/html_res/distinta'
    assert geometry.classname == 'Main'
    assert geometry.canvas == (215.0, 292.0)


def test_scan_follows_inheritance_inside_the_module(tmp_path):
    """A print specializing another print of the same module inherits its page:
    reading only the declaring class would report the subclass as an A4 print."""
    root = write_resources(tmp_path, {'registro': INHERITING_MODULE})
    canvases = dict((geometry.classname, geometry.canvas)
                    for geometry in scanPrintResources(root))
    assert canvases['Base'] == (292.0, 198.0)
    assert canvases['Main'] == (292.0, 198.0)
    #a class that is not a print must not become one because it has the attribute
    assert 'Helper' not in canvases


def test_scan_names_a_secondary_class_apart(tmp_path):
    root = write_resources(tmp_path, {'registro': INHERITING_MODULE})
    names = sorted(geometry.name for geometry in scanPrintResources(root))
    assert names == ['erpy_fatt/resources/tables/fattura/html_res/registro',
                     'erpy_fatt/resources/tables/fattura/html_res/registro:Base']


def test_scan_ignores_a_declaration_that_is_not_a_literal(tmp_path):
    """The resources are read, not imported: a value the reader cannot resolve
    has to fall back to the default rather than be reported as a declaration."""
    root = write_resources(tmp_path, {'computed': COMPUTED_MODULE})
    geometry = scanPrintResources(root)[0]
    assert geometry.declares_page_size is False
    assert geometry.canvas == PAPER_FORMATS['A4']
    assert geometry.templates == 'fattura'


def test_scan_covers_every_package_and_table(tmp_path):
    write_resources(tmp_path, {'distinta': PRINT_MODULE})
    write_resources(tmp_path, {'registro': INHERITING_MODULE},
                    table='mese', package='erpy_coge')
    names = [geometry.name for geometry in scanPrintResources(str(tmp_path))]
    assert names == sorted(names)
    assert len(names) == 3


def test_scan_reads_only_the_print_resource_folder(tmp_path):
    """The print batch wrappers under print/ carry no page geometry: scanning
    them would report a print twice, once without its geometry."""
    root = write_resources(tmp_path, {'distinta': PRINT_MODULE})
    wrapper = tmp_path / 'erpy_fatt' / 'resources' / 'tables' / 'fattura' / 'print'
    wrapper.mkdir()
    (wrapper / 'distinta.py').write_text(PRINT_MODULE)
    assert len(scanPrintResources(root)) == 1


# --- the probe document ------------------------------------------------------

def render(tmp_path, source, **write_kwargs):
    """Render a source document through the real weasyprint service."""
    pytest.importorskip('weasyprint')
    site = make_pdf_site(tmp_path)
    factory = BaseServiceType(site=site, service_type='htmltopdf').getServiceFactory('weasyprint')
    pdf_file = factory(site).writePdf(os.path.basename(source), None, **write_kwargs)
    return pdf_file


def probe_pages(tmp_path, geometry, pages=1, **write_kwargs):
    """The rendered pages of a probe document, as pymupdf pages."""
    fitz = pytest.importorskip('fitz')
    probeDocument(geometry, str(tmp_path / 'probe.html'), pages=pages)
    pdf_file = render(tmp_path, str(tmp_path / 'probe.html'), **write_kwargs)
    try:
        with fitz.open(pdf_file.name) as document:
            return [(page.rect.width, page.rect.height, page.get_text('words'))
                    for page in document]
    finally:
        pdf_file.close()
        os.unlink(pdf_file.name)


def test_probe_carries_the_declared_canvas(tmp_path):
    """The probe is what every print comparison is measured on: a probe whose
    page is not the declared canvas would skew all of them."""
    pages = probe_pages(tmp_path, PrintGeometry('p', page_width=215, page_height=292))
    assert len(pages) == 1
    width, height, _words = pages[0]
    assert abs(width - 215 * MM_TO_PT) < 1
    assert abs(height - 292 * MM_TO_PT) < 1


def test_probe_ruler_words_sit_at_their_millimeter(tmp_path):
    """The ruler is the measuring instrument: its marks must be where they say
    they are, so that a fitted scale of 0.8 means the engine really halved a
    fifth of the print and not that the ruler is wrong."""
    _width, _height, words = probe_pages(tmp_path, PrintGeometry('p'))[0]
    positions = dict((word[4], (word[0], word[1])) for word in words)
    assert positions['p0h000'][0] < 1
    assert abs(positions['p0h100'][0] - 100 * MM_TO_PT) < 2
    assert abs(positions['p0v100'][1] - 100 * MM_TO_PT) < 2


def test_probe_builds_every_requested_page(tmp_path):
    """The marks carry their page number: a comparison pairing words by text
    would otherwise pair a mark of one page with the same mark of another and
    read a pagination difference as a clean fit."""
    pages = probe_pages(tmp_path, PrintGeometry('p'), pages=3)
    assert len(pages) == 3
    texts = [set(word[4] for word in page[2]) for page in pages]
    assert all('p%ih000' % index in texts[index] for index in range(3))
    assert not texts[0] & texts[1]


def test_probe_ruler_stays_inside_the_declared_margins(tmp_path):
    """A print declaring page margins draws inside them: the probe has to start
    there too, otherwise the margins would not be part of what is measured."""
    geometry = PrintGeometry('p', margins=dict(top=15, left=20, bottom=15, right=20))
    _width, _height, words = probe_pages(tmp_path, geometry)[0]
    positions = dict((word[4], (word[0], word[1])) for word in words)
    assert abs(positions['p0h000'][0] - 20 * MM_TO_PT) < 2
    assert abs(positions['p0h000'][1] - 15 * MM_TO_PT) < 2
