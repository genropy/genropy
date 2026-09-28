#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""The page geometry a Genropy print declares, and what each engine makes of it.

A print resource (a :class:`~gnr.web.gnrbaseclasses.TableScriptToHtml` subclass
under ``resources/tables/<table>/html_res``) declares its page as class
attributes: ``page_format`` or an explicit ``page_width``/``page_height``, an
optional ``page_orientation`` and the four ``page_margin_*``. Those millimeters
end up in the html twice: as the ``@page`` rule ``GnrHtmlBuilder`` emits and as
the size of the absolutely positioned page div every page of the print is drawn
into.

The two htmltopdf engines read that html very differently, which is what makes
the declared geometry the starting point of a wkhtmltopdf to weasyprint
migration:

- **weasyprint** honours the ``@page`` rule, so the pdf comes out on a sheet of
  exactly the declared size, drawn at 1:1.
- **wkhtmltopdf** ignores it. The sheet is the one passed on its command line
  (the service passes none, so wkhtmltopdf's own default, A4, in the requested
  orientation) and the layout is scaled to fit the printable width of that
  sheet. That scale is not one number per installation: it is the smaller of a
  constant belonging to the binary and a fit belonging to the print's own
  canvas, so the same binary draws two prints at two different scales
  (:meth:`PrintGeometry.wkScale`). Measured, not assumed:
  :func:`measureWkScale` reports what the installed binary really did to a
  given geometry.

So a print declaring a page no printer ever had (``215x292``, ``292x198``)
prints on plain A4 under wkhtmltopdf and on a 215x292 sheet under weasyprint:
the declared size was never paper, it was the canvas the layout is drawn on.
This module reads those declarations out of a project's print resources
(:func:`scanPrintResources`), resolves them the way
:meth:`~gnr.core.gnrbaghtml.BagToHtml.prepareTemplates` does
(:class:`PrintGeometry`) and builds a measurable document out of one
(:func:`probeDocument`), so that the engine comparison in
:mod:`gnr.utils.htmltopdfdiff` can be run per print instead of per exported
file.
"""

import ast
import os

from gnr.core.gnrhtml import GnrHtmlBuilder
from gnr.core.gnrlang import GnrException
from gnr.utils.htmltopdfdiff import compareEngines

#the page formats BagToHtml implements as format_<name>, as (width, height) in mm
PAPER_FORMATS = {'A4': (210.0, 297.0), 'A5': (148.0, 210.0), 'A6': (105.0, 148.0)}

#the paper wkhtmltopdf falls back to: the htmltopdf wk service passes no page
#size, and pops the page_width/page_height it receives
WK_DEFAULT_PAPER = 'A4'

#wkhtmltopdf's own default page margins, in mm, applied to a document declaring
#@page{margin:0} unless the service passes margin_*
WK_DEFAULT_MARGIN_MM = 10.0

#the print resource base classes whose subclasses declare a page geometry
PRINT_BASE_CLASSES = ('TableScriptToHtml', 'RecordToHtmlNew', 'BagToHtml', 'BagToHtmlWeb')

#the class attributes that make up the declared geometry
GEOMETRY_ATTRIBUTES = ('page_format', 'page_width', 'page_height', 'page_orientation',
                       'page_margin_top', 'page_margin_bottom',
                       'page_margin_left', 'page_margin_right',
                       'templates', 'letterhead_id')


class PrintGeometryError(GnrException):
    pass


def _paperSize(page_format):
    """The (width, height) of a page format in mm, A4 for an unknown one."""
    return PAPER_FORMATS.get(page_format, PAPER_FORMATS['A4'])


class PrintGeometry:
    """The page geometry one print resource declares.

    The declared values are resolved exactly as
    :meth:`~gnr.core.gnrbaghtml.BagToHtml.prepareTemplates` resolves them, so
    :attr:`canvas` is the page size the html really carries: the missing
    dimension comes from ``page_format``, and the orientation orders the two
    sides (an undeclared ``page_orientation`` is deduced from them).

    :param name: the name identifying this print, usually its resource path
    :param source: the file the declaration was read from
    :param classname: the name of the declaring class
    :param page_format: the declared ``page_format``, if any
    :param page_width: the declared ``page_width`` in mm, if any
    :param page_height: the declared ``page_height`` in mm, if any
    :param page_orientation: the declared ``page_orientation``, ``V`` or ``H``
    :param margins: the declared ``page_margin_*``, keyed by side
    :param templates: the declared ``templates`` (a letterhead name)
    :param letterhead_id: the declared ``letterhead_id``"""

    def __init__(self, name, source=None, classname=None, page_format=None,
                 page_width=None, page_height=None, page_orientation=None,
                 margins=None, templates=None, letterhead_id=None):
        self.name = name
        self.source = source
        self.classname = classname
        self.page_format = page_format or 'A4'
        self.page_width = page_width
        self.page_height = page_height
        self.page_orientation = page_orientation
        self.margins = dict(margins or {})
        self.templates = templates
        self.letterhead_id = letterhead_id

    @property
    def declares_page_size(self):
        """True when the print sets ``page_width`` or ``page_height`` itself."""
        return self.page_width is not None or self.page_height is not None

    @property
    def orientation(self):
        """``V`` or ``H``, deduced from the declared sides when not declared."""
        if self.page_orientation:
            return self.page_orientation
        width, height = self._declaredSides()
        return 'V' if height > width else 'H'

    def _declaredSides(self):
        format_width, format_height = _paperSize(self.page_format)
        return (float(self.page_width if self.page_width is not None else format_width),
                float(self.page_height if self.page_height is not None else format_height))

    @property
    def canvas(self):
        """The ``(width, height)`` in mm of the page div the print draws into.

        This is the size ``@page`` carries in the generated html, which is what
        weasyprint prints on and what wkhtmltopdf lays out and shrinks."""
        short_side, long_side = sorted(self._declaredSides())
        if self.orientation == 'V':
            return (short_side, long_side)
        return (long_side, short_side)

    @property
    def wk_orientation(self):
        """The ``--orientation`` the wk service receives for this print.

        :meth:`~gnr.core.gnrbaghtml.BagToHtml.orientation` reads the resolved
        page sides, so it follows :attr:`canvas` and not the declared order."""
        width, height = self.canvas
        return 'Landscape' if width > height else 'Portrait'

    @property
    def wk_paper(self):
        """The ``(width, height)`` in mm wkhtmltopdf really prints this on."""
        short_side, long_side = sorted(_paperSize(WK_DEFAULT_PAPER))
        if self.wk_orientation == 'Landscape':
            return (long_side, short_side)
        return (short_side, long_side)

    @property
    def standard_paper(self):
        """True when the declared canvas is a paper size a printer has.

        A canvas that is not a paper size is the mark of a print laid out
        against wkhtmltopdf: under it the canvas was never the sheet, so any
        value fit, while weasyprint turns it into the sheet itself."""
        width, height = self.canvas
        return any(abs(width - size[0]) < 0.5 and abs(height - size[1]) < 0.5
                   or abs(width - size[1]) < 0.5 and abs(height - size[0]) < 0.5
                   for size in PAPER_FORMATS.values())

    def wkScale(self, shrink=1.0, margin_mm=WK_DEFAULT_MARGIN_MM):
        """The scale wkhtmltopdf draws this print's canvas at.

        Two independent terms decide it, and missing either one is what makes a
        single configured factor unable to describe an installation:

        - ``shrink`` belongs to the **binary**. A build compiled against a stock
          Qt renders a css pixel smaller than a 96dpi pixel and shrinks every
          document by that constant; the official builds, the ones reporting
          "with patched qt" and the ones that drew most clients' prints, do not,
          which is the 1.0 default here. It is not reachable through ``--dpi``
          or ``--zoom``, only through ``--disable-smart-shrinking``, which the
          wk service never passed. Measure it with :func:`measureWkScale` on a
          canvas narrow enough to fit, where this is the only term left.
        - the fit belongs to the **print**. wkhtmltopdf fits the layout into the
          printable width of the sheet, so a print declaring a wide canvas is
          drawn smaller than one declaring a narrow one, by the same binary.

        This is an estimate, not a law. What wkhtmltopdf fits is the widest box
        of the document, which is the page div plus the fraction of a millimeter
        of its borders, and on a build that also shrinks by a constant the two
        terms do not simply take the smaller of the two: measured against an
        official patched build the estimate lands within half a percent, and
        against the stock Qt build of the Ubuntu package within four. Good
        enough to plan a print by, not to decide one by: where half a millimeter
        matters, :func:`measureWkScale` renders that print and measures it.

        :param shrink: the constant shrink of the binary, 1.0 on the official
                       patched builds
        :param margin_mm: the page margin wkhtmltopdf applies, per side
        :returns: the scale, at most ``shrink``"""
        canvas_width = self.canvas[0]
        printable_width = self.wk_paper[0] - 2 * margin_mm
        return min(shrink, printable_width / canvas_width)

    def describe(self):
        """A one line human readable summary of the declared geometry."""
        canvas = '%gx%g' % self.canvas
        paper = '%gx%g' % self.wk_paper
        margins = ','.join('%s=%g' % (side, self.margins[side])
                           for side in ('top', 'bottom', 'left', 'right')
                           if self.margins.get(side))
        parts = ['%s: canvas %smm' % (self.name, canvas)]
        if not self.standard_paper:
            parts.append('not a paper size')
        parts.append('wk prints %smm' % paper)
        if margins:
            parts.append('margins %s' % margins)
        if self.templates or self.letterhead_id:
            parts.append('letterhead %s' % (self.templates or self.letterhead_id))
        return ', '.join(parts)


def _literal(node):
    """The literal value of an assignment, or None when it is not a literal."""
    try:
        return ast.literal_eval(node)
    except (ValueError, SyntaxError):
        return None


def _classAttributes(classnode):
    """The geometry attributes literally assigned in a class body."""
    attributes = {}
    for statement in classnode.body:
        if not isinstance(statement, ast.Assign):
            continue
        for target in statement.targets:
            if isinstance(target, ast.Name) and target.id in GEOMETRY_ATTRIBUTES:
                attributes[target.id] = _literal(statement.value)
    return attributes


def _moduleGeometries(path, name):
    """The geometry of every print class declared in one module.

    Classes are read statically rather than imported: a print resource imports
    the whole web layer and expects a live site, while its page geometry is
    plain class attributes. A class inheriting from another class of the same
    module inherits its attributes too, which is how a print declares the
    geometry once and specializes the content.

    :param path: the module to read
    :param name: the name identifying the print
    :returns: the list of :class:`PrintGeometry` declared there"""
    with open(path, encoding='utf-8') as source_file:
        tree = ast.parse(source_file.read(), filename=path)
    resolved = {}
    geometries = []
    for classnode in [node for node in tree.body if isinstance(node, ast.ClassDef)]:
        bases = [ast.unparse(base).split('.')[-1] for base in classnode.bases]
        inherited = {}
        for base in bases:
            inherited.update(resolved.get(base, {}))
        attributes = dict(inherited, **_classAttributes(classnode))
        resolved[classnode.name] = attributes
        if not any(base in PRINT_BASE_CLASSES or base in resolved for base in bases):
            continue
        geometries.append(PrintGeometry(
            name=name if classnode.name == 'Main' else '%s:%s' % (name, classnode.name),
            source=path, classname=classnode.name,
            page_format=attributes.get('page_format'),
            page_width=attributes.get('page_width'),
            page_height=attributes.get('page_height'),
            page_orientation=attributes.get('page_orientation'),
            margins=dict((side, attributes['page_margin_%s' % side])
                         for side in ('top', 'bottom', 'left', 'right')
                         if attributes.get('page_margin_%s' % side)),
            templates=attributes.get('templates'),
            letterhead_id=attributes.get('letterhead_id')))
    return geometries


def scanPrintResources(root, folder='html_res'):
    """Every print resource of a project, with its declared page geometry.

    :param root: the folder to walk, typically a project's ``packages``
    :param folder: the resource folder print layouts live in
    :returns: the list of :class:`PrintGeometry`, sorted by name"""
    geometries = []
    for dirpath, _dirnames, filenames in os.walk(str(root)):
        if os.path.basename(dirpath) != folder:
            continue
        for filename in sorted(filenames):
            if not filename.endswith('.py') or filename.startswith('__'):
                continue
            path = os.path.join(dirpath, filename)
            name = os.path.relpath(path, str(root))
            geometries.extend(_moduleGeometries(path, os.path.splitext(name)[0]))
    return sorted(geometries, key=lambda geometry: geometry.name)


#the ruler step, in mm: a mark every centimeter is dense enough to fit a
#transform on and sparse enough to stay readable in an overlay
RULER_STEP_MM = 10


def probeDocument(geometry, path, step=RULER_STEP_MM, pages=1):
    """Write a measurable html document with a print's page geometry.

    The document is built through the real :class:`~gnr.core.gnrhtml.GnrHtmlBuilder`,
    so it carries exactly what a print of that geometry carries: the ``@page``
    rule, the page div of the declared canvas and a layout inside the declared
    margins. Its content is a millimeter ruler: words at known positions along
    both axes, which is what lets the engine comparison fit a scale and an
    offset and report them in millimeters of paper.

    :param geometry: the :class:`PrintGeometry` to build
    :param path: where the html is written
    :param step: the distance between two ruler marks, in mm
    :param pages: how many pages to build; a print is rarely one page and the
                  engines have to agree on where the page breaks fall too
    :returns: the written path"""
    width, height = geometry.canvas
    margins = geometry.margins
    builder = GnrHtmlBuilder(page_width=width, page_height=height,
                             page_margin_top=margins.get('top', 0),
                             page_margin_bottom=margins.get('bottom', 0),
                             page_margin_left=margins.get('left', 0),
                             page_margin_right=margins.get('right', 0))
    builder.initializeSrc()
    builder.styleForLayout()
    inner_width = width - margins.get('left', 0) - margins.get('right', 0)
    inner_height = height - margins.get('top', 0) - margins.get('bottom', 0)
    for index in range(pages):
        page = builder.newPage()
        #the page number is part of every mark, so that a comparison pairing the
        #words of two renderings cannot pair a mark of one page with the same
        #mark of another and report a pagination difference as a clean fit
        for offset in range(0, int(inner_width) - step + 1, step):
            page.div('p%ih%03i' % (index, offset),
                     style='position:absolute;top:0mm;left:%imm;font-size:6pt' % offset)
        for offset in range(step, int(inner_height) - step + 1, step):
            page.div('p%iv%03i' % (index, offset),
                     style='position:absolute;top:%imm;left:0mm;font-size:6pt' % offset)
    builder.toHtml(str(path))
    return str(path)


def engineScale(comparison):
    """The scale one engine drew a probe at, relative to the reference one.

    :param comparison: a :class:`gnr.utils.pdfcompare.PdfComparison` of two
                       renderings of the same probe document
    :returns: the mean of the two axis scales of the first page, or None when
              there is no comparable page"""
    if not comparison.pages:
        return None
    page = comparison.pages[0]
    return (page.scale[0] + page.scale[1]) / 2.0


def measureWkScale(site, destFolder, geometry=None, implementation='wk'):
    """Measure how much smaller the installed wkhtmltopdf draws one print.

    The factor is not a property of the binary that can be measured once and
    applied to everything it renders: it follows the canvas each print
    declares, and :meth:`PrintGeometry.wkScale` predicts it to within about a
    percent. Where that is not close enough, and it is not when a print has to
    land on a preprinted form, this renders the print's own probe through both
    engines and reports what the installed binary really did to it.

    So this is measured per print, with that print's geometry, and not once per
    installation.

    :param site: the site (or site facade) the htmltopdf services are bound to
    :param destFolder: a local storage folder the probe and the pdf files are
                       written to
    :param geometry: the :class:`PrintGeometry` to probe with, A4 by default
    :param implementation: the engine to measure
    :returns: the measured factor, or None when the engine did not render"""
    geometry = geometry or PrintGeometry('wkscale')
    folder = site.storageNode(destFolder)
    local = getattr(folder, 'internal_path', None)
    if not local or not os.path.isdir(str(local)):
        raise PrintGeometryError('measuring the wkhtmltopdf scale needs a local '
                                 'destination folder, got %s' % destFolder)
    source = os.path.join(str(local), 'wkscale_probe.html')
    probeDocument(geometry, source)
    result = compareEngines(site, source, destFolder, name='wkscale',
                            orientation=geometry.wk_orientation)
    comparison = result.comparisons.get(implementation)
    return engineScale(comparison) if comparison else None
