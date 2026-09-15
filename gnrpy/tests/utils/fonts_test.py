import importlib
import importlib.util
import json
import os
import shutil
from contextlib import contextmanager

import pytest

from gnr.utils import fonts
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


# ---------- metrics file resolution (#978) ----------

@contextmanager
def gnr_environment(config_dir):
    """Point the genro configuration at *config_dir* and reload font metrics."""
    old = os.environ.get('GENRO_GNRFOLDER')
    os.environ['GENRO_GNRFOLDER'] = str(config_dir)
    try:
        importlib.reload(fonts)
        yield fonts
    finally:
        if old is None:
            del os.environ['GENRO_GNRFOLDER']
        else:
            os.environ['GENRO_GNRFOLDER'] = old
        importlib.reload(fonts)


def make_config(tmp_path, resources_path=None):
    """Build a minimal genro config folder with an environment.xml."""
    config_dir = tmp_path / 'etc' / 'gnr'
    config_dir.mkdir(parents=True)
    resources_tag = ''
    if resources_path is not None:
        resources_tag = '<resources><test path="%s"/></resources>' % resources_path
    (config_dir / 'environment.xml').write_text(
        '<?xml version="1.0"?><GenRoBag>%s</GenRoBag>' % resources_tag)
    return config_dir


def write_metrics(resources_path, widths):
    fonts_dir = resources_path / 'common' / 'fonts'
    fonts_dir.mkdir(parents=True)
    (fonts_dir / 'afm_widths.json').write_text(json.dumps(widths))


def load_module_copy(tmp_dir, module_name):
    """Load a copy of fonts.py from *tmp_dir*, simulating an installed layout."""
    module_path = tmp_dir / 'fonts.py'
    shutil.copy(fonts.__file__.rstrip('c'), str(module_path))
    spec = importlib.util.spec_from_file_location(module_name, str(module_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_no_declaration_finds_shipped_metrics(tmp_path):
    # without a resources declaration the loader still finds the metrics
    # shipped with the code, through the package or the checkout path
    config_dir = make_config(tmp_path)
    with gnr_environment(config_dir) as fonts_mod:
        assert fonts_mod.string_width('A', 'Helvetica', 10) == pytest.approx(6.67)


def test_config_resources_priority(tmp_path):
    # metrics declared in environment.xml win over the ones shipped
    # with the code, like any other overridden shared resource
    resources_path = tmp_path / 'my_resources'
    write_metrics(resources_path, {'Helvetica': {'A': 1000}})
    config_dir = make_config(tmp_path, resources_path)
    with gnr_environment(config_dir) as fonts_mod:
        assert fonts_mod.string_width('A', 'Helvetica', 10) == pytest.approx(10.0)


def test_config_resources_without_file_skipped(tmp_path):
    # a declared resources dir without the metrics file is skipped
    # and the next candidate wins
    resources_path = tmp_path / 'my_resources'
    resources_path.mkdir()
    config_dir = make_config(tmp_path, resources_path)
    with gnr_environment(config_dir) as fonts_mod:
        assert fonts_mod.string_width('A', 'Helvetica', 10) == pytest.approx(6.67)


def test_invalid_metrics_file_skipped(tmp_path):
    # an unreadable metrics file must never break prints:
    # the next candidate wins
    resources_path = tmp_path / 'my_resources'
    fonts_dir = resources_path / 'common' / 'fonts'
    fonts_dir.mkdir(parents=True)
    (fonts_dir / 'afm_widths.json').write_text('{not valid json')
    config_dir = make_config(tmp_path, resources_path)
    with gnr_environment(config_dir) as fonts_mod:
        assert fonts_mod.string_width('A', 'Helvetica', 10) == pytest.approx(6.67)


def test_installed_layout_unconfigured(tmp_path):
    # regression test for #978: on a pip-installed deployment fonts.py lives
    # in site-packages/gnr/utils and the metrics in site-packages/gnr/resources,
    # with no checkout-relative path and nothing declared in environment.xml
    utils_dir = tmp_path / 'site-packages' / 'gnr' / 'utils'
    utils_dir.mkdir(parents=True)
    resources_path = tmp_path / 'site-packages' / 'gnr' / 'resources'
    write_metrics(resources_path, {'Helvetica': {'A': 500}})
    config_dir = make_config(tmp_path)
    with gnr_environment(config_dir):
        installed_fonts = load_module_copy(utils_dir, 'installed_unconfigured_fonts')
        assert installed_fonts.string_width('A', 'Helvetica', 10) == pytest.approx(5.0)


def test_installed_layout_declared_resources_win(tmp_path):
    # the same installed layout, with metrics declared elsewhere:
    # the declaration wins over the ones shipped in the package
    utils_dir = tmp_path / 'site-packages' / 'gnr' / 'utils'
    utils_dir.mkdir(parents=True)
    write_metrics(tmp_path / 'site-packages' / 'gnr' / 'resources',
                  {'Helvetica': {'A': 500}})
    declared_path = tmp_path / 'my_resources'
    write_metrics(declared_path, {'Helvetica': {'A': 800}})
    config_dir = make_config(tmp_path, declared_path)
    with gnr_environment(config_dir):
        installed_fonts = load_module_copy(utils_dir, 'installed_declared_fonts')
        assert installed_fonts.string_width('A', 'Helvetica', 10) == pytest.approx(8.0)


def test_metrics_file_missing_never_raises(tmp_path):
    # worst case of #978: no usable metrics anywhere — string widths must
    # degrade to approximate values instead of raising FileNotFoundError
    utils_dir = tmp_path / 'site-packages' / 'gnr' / 'utils'
    utils_dir.mkdir(parents=True)
    config_dir = make_config(tmp_path)
    with gnr_environment(config_dir):
        installed_fonts = load_module_copy(utils_dir, 'unconfigured_fonts')
        # every char falls back to the default width: 556/1000 * 10pt
        assert installed_fonts.string_width('A', 'Helvetica', 10) == pytest.approx(5.56)
