"""The instance configuration owns the HTTP transport bootstrap option."""

import json
from types import MethodType, SimpleNamespace

import pytest

from gnr.app.gnrapp import GnrApp
from gnr.core.gnrbag import Bag
from gnr.core.gnrclasses import GnrClassCatalog
from gnr.web.gnrwebpage import GnrWebPage


@pytest.mark.parametrize('transport', [None, 'fetch', 'disabled'])
def test_transport_bootstrap_uses_instance_configuration(transport):
    config = Bag()
    if transport:
        config.setItem('experimental.page', None, dojo_xhr_patch=transport)
    application = SimpleNamespace(config=config)
    application.experimentalValue = MethodType(GnrApp.experimentalValue, application)
    static = SimpleNamespace(url=lambda *args: '/static/', internal_path=lambda *args: '/static/' + '/'.join(args))
    page = SimpleNamespace(
        application=application,
        site=SimpleNamespace(
            storage=lambda name: static, debug=False, debugpy=False,
            home_uri='/', compressedJsPath='/client.js', config=Bag()),
        frontend=SimpleNamespace(
            frontend_arg_dict=lambda args: None,
            gnrjs_frontend=lambda: []),
        jstools=SimpleNamespace(compress=lambda files: '/client.js'),
        catalog=GnrClassCatalog(), gnrjsversion='gnr_d11',
        _htmlHeaders=[], charset='utf-8', pagename='test', page_id='test',
        wsk_enabled=False, debug_sql=False, debug_py=False, isMobile=False,
        isDeveloper=lambda: False, deviceScreenSize='desktop', extraFeatures={},
        connection=SimpleNamespace(is_cordova=False, electron_static=False),
        getPwaIntegration=lambda args: None,
        getSquareLogoUrl=lambda args: None,
        getCoverLogoUrl=lambda args: None,
        getGoogleFonts=lambda args: None,
        getSentryJs=lambda args: None,
        get_bodyclasses=lambda: '', get_css_genro=lambda: {}, js_requires=[],
        get_css_path=lambda: ([], {}))

    # Request arguments must neither enable nor disable the instance switch.
    supplied = 'disabled' if transport == 'fetch' else 'fetch'
    result = GnrWebPage.build_arg_dict(page, dojoXhrPatch=supplied)
    start_args = json.loads(result['startArgs'])
    assert start_args['dojoXhrPatch'] == (transport or '')
