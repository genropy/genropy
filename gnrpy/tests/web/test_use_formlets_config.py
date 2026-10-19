"""The instance configuration owns the client default for formlet dialogs."""

import json
from types import MethodType, SimpleNamespace

import pytest

from gnr.app.gnrapp import GnrApp
from gnr.core.gnrbag import Bag
from gnr.core.gnrclasses import GnrClassCatalog
from gnr.web.gnrwebpage import GnrWebPage


def _page(config):
    application = SimpleNamespace(config=config)
    application.experimentalValue = MethodType(GnrApp.experimentalValue, application)
    static = SimpleNamespace(url=lambda *args: '/static/')
    page = SimpleNamespace(
        application=application,
        site=SimpleNamespace(
            storage=lambda name: static, debug=False, debugpy=False,
            home_uri='/', compressedJsPath='/client.js', config=Bag()),
        frontend=SimpleNamespace(
            frontend_arg_dict=lambda args: None,
            gnrjs_frontend=lambda: []),
        catalog=GnrClassCatalog(), gnrjsversion='gnr_d11',
        _htmlHeaders=[], charset='utf-8', pagename='test', page_id='test',
        wsk_enabled=False, wsk=None, debug_sql=False, debug_py=False, isMobile=False,
        isDeveloper=lambda: False, deviceScreenSize='desktop', extraFeatures={},
        connection=SimpleNamespace(is_cordova=False, electron_static=False),
        getPwaIntegration=lambda args: None,
        getSquareLogoUrl=lambda args: None,
        getCoverLogoUrl=lambda args: None,
        getGoogleFonts=lambda args: None,
        getSentryJs=lambda args: None,
        get_bodyclasses=lambda: '', get_css_genro=lambda: {}, js_requires=[],
        get_css_path=lambda: ([], {}))
    page.gnrjs_imports = MethodType(GnrWebPage.gnrjs_imports, page)
    return page


@pytest.mark.parametrize('flag, expected', [
    (None, False), ('true', True), ('True', True), ('false', False), ('', False)])
def test_use_formlets_comes_from_instance_configuration(flag, expected):
    config = Bag()
    if flag is not None:
        config.setItem('gui', None, use_formlets=flag)
    page = _page(config)

    # A request argument must neither enable nor disable the instance switch.
    result = GnrWebPage.build_arg_dict(page, useFormlets=not expected)
    start_args = json.loads(result['startArgs'])
    assert start_args['useFormlets'] == GnrClassCatalog().asTypedText(expected)
