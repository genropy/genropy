#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Geometric comparison of PDF documents rendered by different engines.

Genropy can render a print through two html-to-pdf implementations
(``weasyprint`` and ``wk``, i.e. wkhtmltopdf) and they do not agree. Two
systematic differences show up on the very same html:

* **offset**: wkhtmltopdf applies its own page margins even to a document
  declaring ``@page {margin: 0}``, so the content starts a few millimeters
  inside the page, while weasyprint honours the rule and starts at the corner;
* **scale**: wkhtmltopdf lays the document out on a wide viewport and then fits
  it into the printable area, so the whole content is shrunk by a constant
  factor that weasyprint does not apply.

Telling those two apart matters: an offset is fixed by aligning the margins,
a scale factor is fixed by a zoom, and a *residual* that is neither means the
two engines broke lines or paginated differently and no global setting can
reconcile them.

This module extracts the geometry of a rendered pdf (page sizes, visible ink
bounding box, positioned words) and compares two of them, fitting the best
``position * scale + offset`` transform between matched words on each page and
reporting what the transform cannot explain.

It only needs ``pymupdf`` (a genropy dependency), not the rendering engines, so
a comparison can be replayed on stored pdf files.
"""

import difflib
import os
from dataclasses import dataclass, field

import pymupdf

MM_TO_PT = 72 / 25.4
PT_TO_MM = 25.4 / 72

#a fill lighter than this on every channel is treated as white, i.e. invisible
#ink on white paper: wkhtmltopdf paints the whole printable area with a white
#rectangle, which would otherwise be mistaken for content covering the page
WHITE_THRESHOLD = 0.99

#default tolerance (in points) under which two coordinates are the same point:
#0.5pt is well below a typographic hairline and absorbs the rounding the
#engines apply to the page box itself (595.0 vs 595.28 for A4)
DEFAULT_TOLERANCE_PT = 0.5

#a scale factor differing from 1 by less than this is not a real zoom
DEFAULT_SCALE_TOLERANCE = 0.002


@dataclass(frozen=True)
class Word:
    """A text token with its bounding box, in points from the top-left corner."""

    text: str
    x0: float
    y0: float
    x1: float
    y1: float


@dataclass
class PageGeometry:
    """The measurable geometry of a single rendered page.

    :param index: zero-based page number
    :param width: page box width in points
    :param height: page box height in points
    :param words: the positioned text tokens, in reading order
    :param ink_bbox: bounding box of every visible mark, or None on a blank page"""

    index: int
    width: float
    height: float
    words: list = field(default_factory=list)
    ink_bbox: tuple = None

    @property
    def text(self):
        return ' '.join(word.text for word in self.words)

    @property
    def margins(self):
        """Distance in points between each page edge and the visible content.

        This is what a reader perceives as the margin of the print, whatever
        produced it: a ``@page`` rule, an engine default, or the layout itself.

        :returns: dict keyed ``top``, ``left``, ``bottom``, ``right``, empty on
                  a blank page"""
        if not self.ink_bbox:
            return {}
        x0, y0, x1, y1 = self.ink_bbox
        return dict(top=y0, left=x0, bottom=self.height - y1, right=self.width - x1)

    @property
    def margins_mm(self):
        return {side: value * PT_TO_MM for side, value in self.margins.items()}


@dataclass
class PdfGeometry:
    """The geometry of a whole pdf document.

    :param path: the file the geometry was read from
    :param pages: the list of :class:`PageGeometry`"""

    path: str
    pages: list = field(default_factory=list)

    @property
    def page_count(self):
        return len(self.pages)


def _drawingIsVisible(drawing):
    """True when a vector drawing leaves a visible mark on white paper.

    wkhtmltopdf fills the whole printable area with a white rectangle before
    painting anything else. Counting it as content would make the ink bounding
    box of every wkhtmltopdf page equal to its margin box, hiding the very
    difference this module measures.

    A white mark over a darker background would be visible and is dropped here
    too, which is accepted: prints are laid out on white paper.

    :param drawing: an entry of ``pymupdf.Page.get_drawings()``"""
    colors = [drawing.get('fill'), drawing.get('color')]
    colors = [color for color in colors if color is not None]
    if not colors:
        return False
    return not all(min(color) >= WHITE_THRESHOLD for color in colors)


def _unionBbox(boxes):
    boxes = [box for box in boxes if box is not None]
    if not boxes:
        return None
    return (min(box[0] for box in boxes), min(box[1] for box in boxes),
            max(box[2] for box in boxes), max(box[3] for box in boxes))


def pageGeometry(page, index):
    """Measure one open ``pymupdf`` page.

    :param page: an open ``pymupdf.Page``
    :param index: its zero-based number
    :returns: a :class:`PageGeometry`"""
    words = [Word(text=item[4], x0=item[0], y0=item[1], x1=item[2], y1=item[3])
             for item in page.get_text('words')]
    boxes = [(word.x0, word.y0, word.x1, word.y1) for word in words]
    boxes.extend(tuple(drawing['rect']) for drawing in page.get_drawings()
                 if _drawingIsVisible(drawing))
    boxes.extend(tuple(image['bbox']) for image in page.get_image_info())
    return PageGeometry(index=index, width=page.rect.width, height=page.rect.height,
                        words=words, ink_bbox=_unionBbox(boxes))


def pdfGeometry(path):
    """Read the geometry of a pdf file.

    :param path: path of the pdf to measure
    :returns: a :class:`PdfGeometry`"""
    with pymupdf.open(path) as document:
        pages = [pageGeometry(page, index) for index, page in enumerate(document)]
    return PdfGeometry(path=str(path), pages=pages)


@dataclass
class AxisFit:
    """The best ``scale``/``offset`` transform mapping one axis onto the other.

    ``right = left * scale + offset`` for the matched words of a page.

    :param scale: the fitted multiplier (1.0 when the engines agree on size)
    :param offset: the fitted translation in points
    :param residual: the largest deviation from the fitted transform, in points
    :param samples: how many matched words the fit is based on"""

    scale: float = 1.0
    offset: float = 0.0
    residual: float = 0.0
    samples: int = 0


def fitAxis(pairs):
    """Least-squares fit of ``right = left * scale + offset``.

    With fewer than two distinct left coordinates the scale is not observable
    (any scale fits a single point), so it is pinned to 1 and only the offset
    is fitted: reporting a scale inferred from one word would be noise.

    :param pairs: sequence of ``(left, right)`` coordinates in points
    :returns: an :class:`AxisFit`, whose scale is always strictly positive"""
    pairs = list(pairs)
    if not pairs:
        return AxisFit()
    lefts = [pair[0] for pair in pairs]
    rights = [pair[1] for pair in pairs]
    count = len(pairs)
    mean_left = sum(lefts) / count
    mean_right = sum(rights) / count
    variance = sum((value - mean_left) ** 2 for value in lefts)
    if variance <= 1e-9:
        scale = 1.0
    else:
        covariance = sum((lefts[i] - mean_left) * (rights[i] - mean_right)
                         for i in range(count))
        scale = covariance / variance
    if scale <= 0:
        #a null or negative factor is not a rendering transform: it comes from a
        #degenerate page (every matched word collapsed on one coordinate) and
        #would make the aligned rasterization divide by zero. Report the
        #translation alone and let the residual expose what is left
        scale = 1.0
    offset = mean_right - scale * mean_left
    residual = max(abs(rights[i] - (lefts[i] * scale + offset)) for i in range(count))
    return AxisFit(scale=scale, offset=offset, residual=residual, samples=count)


def matchWords(left_words, right_words):
    """Pair the words of two pages by their text, in reading order.

    Uses a sequence match so that words present on one side only (a header the
    other engine dropped, a differently hyphenated run) are skipped instead of
    shifting every following pair and poisoning the fit.

    :param left_words: the :class:`Word` list of the left page
    :param right_words: the :class:`Word` list of the right page
    :returns: list of ``(left_word, right_word)`` tuples"""
    matcher = difflib.SequenceMatcher(None, [word.text for word in left_words],
                                      [word.text for word in right_words], autojunk=False)
    pairs = []
    for left_start, right_start, size in matcher.get_matching_blocks():
        for offset in range(size):
            pairs.append((left_words[left_start + offset], right_words[right_start + offset]))
    return pairs


@dataclass
class PageComparison:
    """The differences found between two renderings of the same page.

    :param index: zero-based page number
    :param left: the left :class:`PageGeometry`
    :param right: the right :class:`PageGeometry`
    :param x_fit: the horizontal :class:`AxisFit`, None when nothing matched
    :param y_fit: the vertical :class:`AxisFit`, None when nothing matched
    :param unmatched_left: words found only on the left page
    :param unmatched_right: words found only on the right page"""

    index: int
    left: PageGeometry
    right: PageGeometry
    x_fit: AxisFit = None
    y_fit: AxisFit = None
    unmatched_left: list = field(default_factory=list)
    unmatched_right: list = field(default_factory=list)
    tolerance_pt: float = DEFAULT_TOLERANCE_PT
    scale_tolerance: float = DEFAULT_SCALE_TOLERANCE

    @property
    def page_size_delta(self):
        """``(width, height)`` difference in points between the two page boxes."""
        return (self.right.width - self.left.width, self.right.height - self.left.height)

    @property
    def same_page_size(self):
        return all(abs(delta) <= self.tolerance_pt for delta in self.page_size_delta)

    @property
    def margin_delta(self):
        """Per-side difference in points between the two content margins."""
        left_margins = self.left.margins
        right_margins = self.right.margins
        if not left_margins or not right_margins:
            return {}
        return {side: right_margins[side] - left_margins[side] for side in left_margins}

    @property
    def margin_delta_mm(self):
        return {side: value * PT_TO_MM for side, value in self.margin_delta.items()}

    @property
    def same_text(self):
        return not self.unmatched_left and not self.unmatched_right

    @property
    def offset_pt(self):
        """``(x, y)`` translation the right rendering applies to the left one."""
        return (self.x_fit.offset if self.x_fit else 0.0,
                self.y_fit.offset if self.y_fit else 0.0)

    @property
    def offset_mm(self):
        return tuple(value * PT_TO_MM for value in self.offset_pt)

    @property
    def scale(self):
        """``(x, y)`` factor the right rendering applies to the left one."""
        return (self.x_fit.scale if self.x_fit else 1.0,
                self.y_fit.scale if self.y_fit else 1.0)

    @property
    def residual_pt(self):
        """Largest deviation left by the fitted transform, in points.

        A residual above the tolerance means the difference is *not* a global
        offset or zoom: the engines broke lines or placed blocks differently and
        no margin or zoom setting will align them."""
        return max(self.x_fit.residual if self.x_fit else 0.0,
                   self.y_fit.residual if self.y_fit else 0.0)

    @property
    def has_offset(self):
        return any(abs(value) > self.tolerance_pt for value in self.offset_pt)

    @property
    def has_scale(self):
        return any(abs(value - 1.0) > self.scale_tolerance for value in self.scale)

    @property
    def has_residual(self):
        return self.residual_pt > self.tolerance_pt

    @property
    def identical(self):
        return not (self.has_offset or self.has_scale or self.has_residual
                    or not self.same_text or not self.same_page_size)

    def describe(self):
        """A one-line human readable summary of this page."""
        if self.identical:
            return 'page %i: identical' % (self.index + 1)
        notes = []
        if not self.same_page_size:
            notes.append('page size %+.2f x %+.2f pt' % self.page_size_delta)
        if not self.same_text:
            notes.append('text differs (%i only-left, %i only-right)'
                         % (len(self.unmatched_left), len(self.unmatched_right)))
        if self.has_offset:
            notes.append('offset %+.2f x %+.2f mm' % self.offset_mm)
        if self.has_scale:
            notes.append('scale %.4f x %.4f' % self.scale)
        if self.has_residual:
            notes.append('residual %.2f pt' % self.residual_pt)
        if not notes:
            notes.append('no measurable difference')
        return 'page %i: %s' % (self.index + 1, ', '.join(notes))


@dataclass
class PdfComparison:
    """The full comparison of two renderings of the same source document.

    :param left: geometry of the reference rendering
    :param right: geometry of the rendering under comparison
    :param pages: the per-page :class:`PageComparison` list, over the pages both
                  documents have"""

    left: PdfGeometry
    right: PdfGeometry
    pages: list = field(default_factory=list)
    left_label: str = 'left'
    right_label: str = 'right'

    @property
    def same_page_count(self):
        return self.left.page_count == self.right.page_count

    @property
    def identical(self):
        return self.same_page_count and all(page.identical for page in self.pages)

    @property
    def max_offset_mm(self):
        """The largest absolute translation over every page, in millimeters."""
        if not self.pages:
            return 0.0
        return max(max(abs(value) for value in page.offset_mm) for page in self.pages)

    @property
    def max_residual_pt(self):
        if not self.pages:
            return 0.0
        return max(page.residual_pt for page in self.pages)

    def describe(self):
        """A multi line human readable summary of the whole comparison."""
        lines = ['%s vs %s' % (self.left_label, self.right_label)]
        if not self.same_page_count:
            lines.append('page count differs: %i vs %i'
                         % (self.left.page_count, self.right.page_count))
        lines.extend(page.describe() for page in self.pages)
        return '\n'.join(lines)


def comparePdf(left_path, right_path, tolerance_pt=DEFAULT_TOLERANCE_PT,
               scale_tolerance=DEFAULT_SCALE_TOLERANCE,
               left_label=None, right_label=None):
    """Compare two pdf files rendered from the same source document.

    Pages are compared pairwise up to the shorter document: a page count
    mismatch is reported on its own (``same_page_count``) and the pages both
    documents have are still measured, so a pagination difference does not hide
    the margin difference that probably caused it.

    :param left_path: reference pdf (by convention the weasyprint rendering)
    :param right_path: pdf to compare against the reference
    :param tolerance_pt: distance in points under which coordinates are equal
    :param scale_tolerance: deviation from 1.0 under which a scale is not a zoom
    :param left_label: name of the left rendering in the summaries
    :param right_label: name of the right rendering in the summaries
    :returns: a :class:`PdfComparison`"""
    left = pdfGeometry(left_path)
    right = pdfGeometry(right_path)
    return compareGeometry(left, right, tolerance_pt=tolerance_pt,
                           scale_tolerance=scale_tolerance,
                           left_label=left_label or os.path.basename(str(left_path)),
                           right_label=right_label or os.path.basename(str(right_path)))


def compareGeometry(left, right, tolerance_pt=DEFAULT_TOLERANCE_PT,
                    scale_tolerance=DEFAULT_SCALE_TOLERANCE,
                    left_label='left', right_label='right'):
    """Compare two already measured documents.

    :param left: reference :class:`PdfGeometry`
    :param right: :class:`PdfGeometry` to compare against the reference
    :returns: a :class:`PdfComparison`"""
    pages = []
    for index in range(min(left.page_count, right.page_count)):
        left_page = left.pages[index]
        right_page = right.pages[index]
        pairs = matchWords(left_page.words, right_page.words)
        matched_left = {id(pair[0]) for pair in pairs}
        matched_right = {id(pair[1]) for pair in pairs}
        comparison = PageComparison(
            index=index, left=left_page, right=right_page,
            x_fit=fitAxis([(pair[0].x0, pair[1].x0) for pair in pairs]) if pairs else None,
            y_fit=fitAxis([(pair[0].y0, pair[1].y0) for pair in pairs]) if pairs else None,
            unmatched_left=[word for word in left_page.words if id(word) not in matched_left],
            unmatched_right=[word for word in right_page.words if id(word) not in matched_right],
            tolerance_pt=tolerance_pt, scale_tolerance=scale_tolerance)
        pages.append(comparison)
    return PdfComparison(left=left, right=right, pages=pages,
                         left_label=left_label, right_label=right_label)


def pageTransform(comparison):
    """The ``(scale_x, scale_y, offset_x, offset_y)`` the right rendering applies.

    Feeding it back to :func:`renderPagePixmap` undoes the offset and the zoom,
    so the raster comparison shows what is left once the two systematic
    differences are compensated.

    :param comparison: a :class:`PageComparison`
    :returns: a 4-tuple of floats"""
    scale_x, scale_y = comparison.scale
    offset_x, offset_y = comparison.offset_pt
    return (scale_x, scale_y, offset_x, offset_y)


def renderPagePixmap(path, index=0, dpi=100, transform=None, size=None):
    """Rasterize one page in grayscale, optionally undoing a transform.

    The transform is undone by rasterizing the region of this page that
    corresponds to the whole reference page, rescaled to the reference size.
    Expressing it as a clip rather than as a translation in the render matrix
    is deliberate: pymupdf anchors the produced pixmap on the transformed clip
    origin, so a translation carried by the matrix is normalized away and the
    two rasterizations would come out exactly as misaligned as before.

    :param path: the pdf file
    :param index: zero-based page number
    :param dpi: rasterization resolution
    :param transform: ``(scale_x, scale_y, offset_x, offset_y)`` to undo, as
                      returned by :func:`pageTransform`; None renders the page
                      as it is
    :param size: ``(width, height)`` in pixels the result must have, padded
                 with white or cropped; None keeps the natural size
    :returns: a grayscale ``pymupdf.Pixmap``"""
    zoom = dpi / 72.0
    with pymupdf.open(path) as document:
        page = document[index]
        if transform:
            scale_x, scale_y, offset_x, offset_y = transform
            clip = pymupdf.Rect(offset_x, offset_y,
                                offset_x + page.rect.width * scale_x,
                                offset_y + page.rect.height * scale_y)
            matrix = pymupdf.Matrix(zoom / scale_x, zoom / scale_y)
        else:
            clip = page.rect
            matrix = pymupdf.Matrix(zoom, zoom)
        pixmap = page.get_pixmap(matrix=matrix, colorspace=pymupdf.csGRAY, clip=clip)
    if size and (pixmap.width, pixmap.height) != tuple(size):
        pixmap = _resizedPixmap(pixmap, size[0], size[1])
    return pixmap


def _resizedPixmap(pixmap, width, height):
    """A grayscale pixmap padded with white (or cropped) to the given size.

    The engines round the page box differently (595.0 against 595.28 points for
    A4), so the same page rasterized at the same dpi can come out a pixel wider
    on one side. Padding on the right and bottom keeps both images anchored on
    the top-left corner instead of shearing every row.

    :param pixmap: a grayscale ``pymupdf.Pixmap``
    :param width: target width in pixels
    :param height: target height in pixels"""
    padded = bytearray(b'\xff' * (width * height))
    source = pixmap.samples
    copy_width = min(pixmap.width, width)
    for row in range(min(pixmap.height, height)):
        source_start = row * pixmap.width
        target_start = row * width
        padded[target_start:target_start + copy_width] = \
            source[source_start:source_start + copy_width]
    return pymupdf.Pixmap(pymupdf.csGRAY, width, height, bytes(padded), False)


def pixmapDiffRatio(left_pixmap, right_pixmap, threshold=16):
    """Fraction of the area where two grayscale pixmaps differ.

    :param threshold: per-pixel gray difference below which the pixel counts as
                      equal, absorbing the antialiasing noise the two
                      rasterizations leave on the very same glyph
    :returns: a float between 0.0 (identical) and 1.0"""
    width = max(left_pixmap.width, right_pixmap.width)
    height = max(left_pixmap.height, right_pixmap.height)
    left_samples = _resizedPixmap(left_pixmap, width, height).samples
    right_samples = _resizedPixmap(right_pixmap, width, height).samples
    different = sum(1 for left_value, right_value in zip(left_samples, right_samples)
                    if abs(left_value - right_value) > threshold)
    return different / float(width * height) if width and height else 0.0


def overlayPixmap(left_pixmap, right_pixmap):
    """Merge two grayscale pixmaps into one false-color RGB overlay.

    The left rendering drives the red channel and the right one drives green
    and blue: shared ink stays black, ink only in the left rendering shows up
    cyan, ink only in the right one shows up red. Two renderings that agree
    come out as a plain black and white page, which makes a whole report
    scannable at a glance.

    :returns: an RGB ``pymupdf.Pixmap``"""
    width = max(left_pixmap.width, right_pixmap.width)
    height = max(left_pixmap.height, right_pixmap.height)
    left_samples = _resizedPixmap(left_pixmap, width, height).samples
    right_samples = _resizedPixmap(right_pixmap, width, height).samples
    overlay = bytearray(width * height * 3)
    overlay[0::3] = left_samples
    overlay[1::3] = right_samples
    overlay[2::3] = right_samples
    return pymupdf.Pixmap(pymupdf.csRGB, width, height, bytes(overlay), False)


def pageOverlay(left_path, right_path, index=0, dpi=100, transform=None):
    """False-color overlay of the same page of two pdf files.

    :param transform: ``(scale_x, scale_y, offset_x, offset_y)`` applied to the
                      right rendering to undo it before overlaying, as returned
                      by :func:`pageTransform`; None overlays the pages as they
                      are, showing the raw difference
    :returns: an RGB ``pymupdf.Pixmap``"""
    left_pixmap = renderPagePixmap(left_path, index=index, dpi=dpi)
    right_pixmap = renderPagePixmap(right_path, index=index, dpi=dpi,
                                    transform=transform,
                                    size=(left_pixmap.width, left_pixmap.height))
    return overlayPixmap(left_pixmap, right_pixmap)


def pageInkDiffRatio(left_path, right_path, index=0, dpi=100, threshold=16,
                     transform=None):
    """Fraction of the page area where two renderings differ visually.

    Complements the geometric comparison: it catches what no word position can
    express (a border that did not print, a background fill, an image scaled
    differently).

    Without a transform this measures the raw difference, which on a print
    whose only problem is a three millimeter offset is close to the whole inked
    area: everything differs because everything moved. Passing the transform of
    the matching :class:`PageComparison` answers the question that actually
    matters, whether the renderings differ *beyond* the offset and the zoom.

    :param transform: ``(scale_x, scale_y, offset_x, offset_y)`` to undo on the
                      right rendering, as returned by :func:`pageTransform`
    :returns: a float between 0.0 (identical) and 1.0"""
    left_pixmap = renderPagePixmap(left_path, index=index, dpi=dpi)
    right_pixmap = renderPagePixmap(right_path, index=index, dpi=dpi,
                                    transform=transform,
                                    size=(left_pixmap.width, left_pixmap.height))
    return pixmapDiffRatio(left_pixmap, right_pixmap, threshold=threshold)
