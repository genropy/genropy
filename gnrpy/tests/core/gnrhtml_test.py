from gnr.core import gnrhtml  # noqa: F401
from gnr.core.gnrhtml import GnrHtmlBuilder, MM_TO_PT


def test():
    pass


class FakeBuilder:
    """Minimal stub that provides the page-dimension attributes used by
    GnrHtmlBuilder.calcRowsNumber when width_mm is not supplied."""
    font_family = 'Helvetica'
    font_size = 10
    page_width = 200
    page_margin_left = 10
    page_margin_right = 10

    calcRowsNumber = GnrHtmlBuilder.calcRowsNumber


def _builder(**kwargs):
    b = FakeBuilder()
    for k, v in kwargs.items():
        setattr(b, k, v)
    return b


def test_calcRowsNumber_empty():
    assert FakeBuilder().calcRowsNumber('') == 0


def test_calcRowsNumber_single_word():
    assert FakeBuilder().calcRowsNumber('Hello') == 1


def test_calcRowsNumber_short_line_fits():
    # 'Hello world' at 10pt Helvetica is well under 180mm available width
    assert FakeBuilder().calcRowsNumber('Hello world') == 1


def test_calcRowsNumber_explicit_newline():
    assert FakeBuilder().calcRowsNumber('line one\nline two') == 2


def test_calcRowsNumber_multiple_explicit_newlines():
    assert FakeBuilder().calcRowsNumber('a\nb\nc') == 3


def test_calcRowsNumber_wraps_long_text():
    # Use a very narrow column (10mm) so words always overflow to the next line
    b = _builder(font_family='Courier', font_size=10)
    # Each word is longer than 10mm * MM_TO_PT = ~28.3pt; 'Hello' in Courier
    # at 10pt = 5 * 6pt = 30pt > 28.3pt so each word lands on its own line
    avail_mm = 10
    result = b.calcRowsNumber('Hello World Foo', width_mm=avail_mm)
    assert result == 3


def test_calcRowsNumber_mm_to_pt_constant():
    assert MM_TO_PT == 72 / 25.4
