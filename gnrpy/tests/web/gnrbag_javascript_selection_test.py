import pytest

from gnr.web.gnrwebpage_proxy.frontend.dojo_11 import GnrWebFrontend


class FakeApplication:
    def __init__(self, implementation=None):
        self.implementation = implementation

    def experimentalValue(self, group, name):
        assert (group, name) == ('bag_js', 'implementation')
        return self.implementation


def frontend(implementation=None):
    result = GnrWebFrontend.__new__(GnrWebFrontend)
    result.page = type('Page', (), {'application': FakeApplication(implementation)})()
    return result


@pytest.mark.parametrize('implementation', [None, 'legacy'])
def test_legacy_bag_is_the_default(implementation):
    imports = frontend(implementation).gnrjs_frontend()
    assert imports[:2] == ['gnrbag', 'gnrdomsource']
    assert 'genro_bagjs_bundle' not in imports


def test_removed_adapter_selection_fails_explicitly():
    with pytest.raises(ValueError, match='Unsupported JavaScript Bag implementation: genro-bag-js'):
        frontend('genro-bag-js').gnrjs_frontend()


def test_unknown_bag_implementation_fails_explicitly():
    with pytest.raises(ValueError, match='Unsupported JavaScript Bag implementation: unknown'):
        frontend('unknown').gnrjs_frontend()



def test_lightweight_mixin_precedes_consumers():
    imports = frontend('genro-bag-js-mixin').gnrjs_frontend()
    assert imports[:3] == ['genro_bagjs_bundle', 'gnrbag_mixin', 'gnrdomsource']
    assert 'gnrbag_genro' not in imports
    assert 'gnrbag' not in imports



def test_page_override_does_not_change_other_pages_on_same_application():
    first = frontend('genro-bag-js-mixin')
    second = frontend()
    second.page.application = first.page.application
    first.page.bag_js_implementation = 'legacy'
    assert first.gnrjs_frontend()[0] == 'gnrbag'
    assert second.gnrjs_frontend()[:2] == ['genro_bagjs_bundle', 'gnrbag_mixin']


def test_native_frontend_ignores_instance_mixin_and_excludes_genro_consumers():
    from gnr.web.gnrwebpage_proxy.frontend.bag_native import GnrWebFrontend as Native
    page = frontend('genro-bag-js-mixin').page
    page.page_frontend = 'bag_native'
    page.pagetemplate = 'my_native_page.tpl'
    native = Native.__new__(Native)
    native.page = page
    native.init()
    assert native.gnrjs_frontend() == ['genro_bagjs_bundle']
    assert native.importer() == ''
    assert native.css_genro_frontend() == {}
    page.pagetemplate = 'standard.tpl'
    with pytest.raises(ValueError, match='custom HTML template'):
        native.init()


def test_compressed_cache_is_keyed_by_ordered_asset_paths():
    from types import SimpleNamespace
    from gnr.web.gnrjsassets import compressed_javascript_url
    calls = []

    def compress(files):
        calls.append(list(files))
        return f'/bundle-{len(calls)}.js'

    site = SimpleNamespace(debug=False, compressedJsPath='/old-global.js')
    page = SimpleNamespace(site=site, jstools=SimpleNamespace(compress=compress),
                           application=FakeApplication('genro-bag-js-mixin'))
    native = ['bundle.js']
    mixed = ['bundle.js', 'mixin.js']
    assert compressed_javascript_url(page, native) == '/bundle-1.js'
    assert compressed_javascript_url(page, mixed) == '/bundle-2.js'
    assert compressed_javascript_url(page, native) == '/bundle-1.js'
    assert compressed_javascript_url(page, list(reversed(mixed))) == '/bundle-3.js'
    site.debug = True
    assert compressed_javascript_url(page, native) == '/bundle-4.js'
    assert len(calls) == 4


@pytest.mark.parametrize('native_first', [False, True])
def test_legacy_cache_is_preserved_on_a_site_with_native_pages(native_first):
    from types import SimpleNamespace
    from gnr.web.gnrjsassets import compressed_javascript_url
    calls = []

    def compress(files):
        calls.append(list(files))
        return f'/bundle-{len(calls)}.js'

    site = SimpleNamespace(debug=False, compressedJsPath=None)
    application = FakeApplication()
    legacy = SimpleNamespace(site=site, application=application,
                             jstools=SimpleNamespace(compress=compress))
    native = SimpleNamespace(site=site, application=application,
                             page_frontend='bag_native', jstools=legacy.jstools)
    for page, files in ([(native, ['native.js']), (legacy, ['legacy.js'])]
                        if native_first else
                        [(legacy, ['legacy.js']), (native, ['native.js'])]):
        compressed_javascript_url(page, files)
    legacy_url = compressed_javascript_url(legacy, ['legacy.js'])
    native_url = compressed_javascript_url(native, ['native.js'])
    assert legacy_url != native_url
    assert site.compressedJsPath == legacy_url
    assert len(calls) == 2

    # Applications may replace the legacy URL; native pages must not use it.
    site.compressedJsPath = '/custom.js'
    assert compressed_javascript_url(legacy, ['legacy.js']) == '/custom.js'
    assert compressed_javascript_url(native, ['native.js']) == native_url
    assert len(calls) == 2
    site.debug = True
    assert compressed_javascript_url(legacy, ['legacy.js']) == '/bundle-3.js'
    assert site.compressedJsPath == '/bundle-3.js'
    assert compressed_javascript_url(native, ['native.js']) == '/bundle-4.js'
    assert site.compressedJsPath == '/bundle-3.js'
