import pytest

from gnr.utils.fonts import resolve_font_name, font_size_pt, string_width


# ---------- resolve_font_name ----------

def test_resolve_direct_name():
    assert resolve_font_name('Helvetica') == 'Helvetica'
    assert resolve_font_name('Courier-Bold') == 'Courier-Bold'


def test_resolve_alias_case_insensitive():
    assert resolve_font_name('Arial') == 'Helvetica'
    assert resolve_font_name('arial') == 'Helvetica'
    assert resolve_font_name('Times New Roman') == 'Times-Roman'


def test_resolve_narrow_alias():
    assert resolve_font_name('Arial Narrow') == 'Helvetica-Narrow'
    assert resolve_font_name('Liberation Sans Narrow') == 'Helvetica-Narrow'


def test_resolve_css_stack_first_mapped_wins():
    stack = '"Arial Narrow", "Liberation Sans Narrow", sans-serif'
    assert resolve_font_name(stack) == 'Helvetica-Narrow'


def test_resolve_css_stack_skips_unknown_entries():
    assert resolve_font_name('Comic Sans MS, Courier') == 'Courier'


def test_resolve_generic_families():
    assert resolve_font_name('sans-serif') == 'Helvetica'
    assert resolve_font_name('serif') == 'Times-Roman'
    assert resolve_font_name('monospace') == 'Courier'


def test_resolve_fallback_default():
    assert resolve_font_name('UnknownFont') == 'Helvetica'
    assert resolve_font_name(None) == 'Helvetica'
    assert resolve_font_name('') == 'Helvetica'
    assert resolve_font_name('UnknownFont', default='Courier') == 'Courier'


# ---------- derived narrow metrics ----------

def test_narrow_widths_derived_from_base_font():
    base = string_width('Sample text', 'Helvetica', 10)
    narrow = string_width('Sample text', 'Helvetica-Narrow', 10)
    assert narrow == pytest.approx(base * 0.82)


def test_narrow_of_unknown_base_falls_back_to_helvetica():
    assert string_width('abc', 'Nonexistent-Narrow', 10) == string_width('abc', 'Helvetica', 10)


# ---------- font_size_pt ----------

def test_font_size_pt_numeric():
    assert font_size_pt(9) == 9.0
    assert font_size_pt(10.5) == 10.5


def test_font_size_pt_pt_string():
    assert font_size_pt('9pt') == 9.0
    assert font_size_pt(' 11PT ') == 11.0


def test_font_size_pt_px_string():
    assert font_size_pt('12px') == 9.0


def test_font_size_pt_invalid_returns_default():
    assert font_size_pt('large') == 10.0
    assert font_size_pt(None) == 10.0
    assert font_size_pt('large', default=8) == 8.0
