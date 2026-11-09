import os

import pytest

from gnr.web.gnrwebpage import GnrWebPage

RESOURCES = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'resources'))


@pytest.mark.parametrize('key,path', sorted(GnrWebPage._VENDORED_BUNDLES.items()))
def test_vendored_bundle_is_on_disk(key, path):
    assert os.path.isfile(os.path.join(RESOURCES, *path)), key


def test_jodit_bundle_is_published():
    assert GnrWebPage._VENDORED_BUNDLES['jodit'] == ('js_libs', 'jodit', 'jodit.min.js')
    assert GnrWebPage._VENDORED_BUNDLES['joditCss'] == ('js_libs', 'jodit', 'jodit.min.css')
