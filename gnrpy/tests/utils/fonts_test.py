# -*- coding: utf-8 -*-
import importlib
import importlib.util
import json
import os
import shutil
from contextlib import contextmanager

import pytest

from gnr.utils import fonts


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


def test_checkout_relative_fallback(tmp_path):
    # without a resources declaration the loader falls back to the
    # checkout-relative path and still finds the real metrics
    config_dir = make_config(tmp_path)
    with gnr_environment(config_dir) as fonts_mod:
        assert fonts_mod.string_width('A', 'Helvetica', 10) == pytest.approx(6.67)


def test_config_resources_priority(tmp_path):
    # metrics resolved through the environment.xml resources declaration
    # win over the checkout-relative fallback
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


def test_installed_layout(tmp_path):
    # regression test for issue #977: simulate a pip-installed deployment
    # where fonts.py lives in site-packages/gnr/utils, the metrics file in
    # site-packages/gnr/resources and no checkout-relative path exists
    utils_dir = tmp_path / 'site-packages' / 'gnr' / 'utils'
    utils_dir.mkdir(parents=True)
    resources_path = tmp_path / 'site-packages' / 'gnr' / 'resources'
    write_metrics(resources_path, {'Helvetica': {'A': 500}})
    config_dir = make_config(tmp_path, resources_path)
    with gnr_environment(config_dir):
        installed_fonts = load_module_copy(utils_dir, 'installed_fonts')
        assert installed_fonts.string_width('A', 'Helvetica', 10) == pytest.approx(5.0)


def test_installed_layout_unconfigured_never_raises(tmp_path):
    # worst case of issue #977: installed layout and no usable resources
    # declaration — string_width must degrade to approximate widths
    # instead of raising FileNotFoundError
    utils_dir = tmp_path / 'site-packages' / 'gnr' / 'utils'
    utils_dir.mkdir(parents=True)
    config_dir = make_config(tmp_path)
    with gnr_environment(config_dir):
        installed_fonts = load_module_copy(utils_dir, 'unconfigured_fonts')
        # every char falls back to the default width: 556/1000 * 10pt
        assert installed_fonts.string_width('A', 'Helvetica', 10) == pytest.approx(5.56)
