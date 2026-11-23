"""The chip caption of attachmentChips is HTML written into innerHTML by the multibutton:
everything that comes from the attachment (its description, its extension) must reach it
escaped, since the description is the uploaded file name and can be renamed by the user."""

import importlib.util
import os

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
ATTACHMANAGER = os.path.join(REPO_ROOT, 'resources', 'common', 'gnrcomponents',
                             'attachmanager', 'attachmanager.py')


def _attachmanager():
    spec = importlib.util.spec_from_file_location('attachmanager_under_test', ATTACHMANAGER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_markup_in_the_description_is_escaped():
    caption = _attachmanager().chipCaption(description='<img src=x onerror=alert(1)>',
                                           ext='.png', size=10, kind='image')
    assert '<img' not in caption
    assert '&lt;img src=x onerror=alert(1)&gt;' in caption


def test_markup_in_the_extension_is_escaped():
    caption = _attachmanager().chipCaption(description='report', ext='.<b>x', size=None, kind='file')
    assert '<b>' not in caption
    assert '&lt;B&gt;X' in caption


def test_caption_carries_kind_name_extension_and_size():
    caption = _attachmanager().chipCaption(description='order', ext='.pdf', size=2048, kind='pdf')
    assert 'atc_chip_pdf' in caption
    assert '<span class="atc_chip_name">order</span>' in caption
    assert '<span class="atc_chip_meta">PDF 2.0 KB</span>' in caption


def test_no_meta_without_extension_and_size():
    caption = _attachmanager().chipCaption(description='link', ext='', size=None, kind='link')
    assert 'atc_chip_meta' not in caption
