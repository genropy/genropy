# -*- coding: utf-8 -*-
"""Tests for the no-mako rootPage rendering path.

These tests verify that the struct-based templates produce functionally
equivalent HTML to the Mako templates: same tags, same attributes,
same scripts and styles, same structure.
"""

import importlib.util
import os
import re


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
STRUCT_TPL_DIR = os.path.join(REPO_ROOT, 'resources', 'common', 'tpl')
MAKO_TPL_DIR = os.path.join(REPO_ROOT, 'gnrjs', 'gnr_d11', 'tpl')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_arg_dict(**overrides):
    """Return a realistic arg_dict similar to what build_arg_dict produces."""
    d = dict(
        charset='utf-8',
        page_id='test_page_001',
        baseUrl='/',
        pageMode='wsgi_10',
        pageModule='/path/to/index.py',
        filename='index',
        bodyclasses='claro tundra',
        gnrModulePath='/_rsrc/gnr_d11',
        dojolib='/_rsrc/gnr_d11/lib/dojo/dojo.js',
        djConfig='parseOnLoad: false',
        genroJsImport=['/_rsrc/gnr_d11/js/genro.js',
                       '/_rsrc/gnr_d11/js/genro_rpc.js'],
        dijitImport=[],
        customHeaders=[],
        js_requires=['/_rsrc/common/public.js'],
        css_dojo=['/_rsrc/gnr_d11/lib/dojo/resources/dojo.css'],
        css_genro={'all': ['/_rsrc/gnr_d11/css/genro.css']},
        css_requires=['/_rsrc/common/public.css'],
        css_media_requires={'print': ['/_rsrc/gnr_d11/css/gnrprint.css']},
        startArgs='{}',
        pwa=False,
        sentryjs=None,
        favicon=None,
        google_fonts=None,
        logo_url=None,
        staging_style='',
        staging_colour='',
        sentry_sample_rate='0.0',
        sentry_traces_sample_rate='0.0',
        sentry_profiles_sample_rate='0.0',
        sentry_replays_session_sample_rate='0.0',
        sentry_replays_on_error_sample_rate='0.0',
    )
    d.update(overrides)
    return d


def _render_struct(arg_dict):
    """Render the struct-based standard.py template."""
    mod_path = os.path.join(STRUCT_TPL_DIR, 'standard.py')
    spec = importlib.util.spec_from_file_location('test_standard_tpl', mod_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    PageTemplate = mod.PageTemplate

    class FakePage(object):
        tpldirectories = [STRUCT_TPL_DIR, MAKO_TPL_DIR]

    return PageTemplate(FakePage()).render(arg_dict)


# ---------------------------------------------------------------------------
# Tests: Document structure
# ---------------------------------------------------------------------------

class TestDocumentStructure:
    """The struct template produces a valid XHTML document."""

    def test_has_xml_declaration(self):
        html = _render_struct(_make_arg_dict())
        assert '<?xml version="1.0"' in html

    def test_has_doctype(self):
        html = _render_struct(_make_arg_dict())
        assert '<!DOCTYPE html' in html

    def test_has_xhtml_namespace(self):
        html = _render_struct(_make_arg_dict())
        assert 'xmlns="http://www.w3.org/1999/xhtml"' in html

    def test_has_html_head_body(self):
        html = _render_struct(_make_arg_dict()).lower()
        assert '<html' in html
        assert '<head>' in html or '<head ' in html
        assert '<body' in html

    def test_is_pretty_printed(self):
        html = _render_struct(_make_arg_dict())
        lines = html.strip().splitlines()
        assert len(lines) > 10
        indented = [l for l in lines if l.startswith('\t')]
        assert len(indented) > 5


# ---------------------------------------------------------------------------
# Tests: Meta tags
# ---------------------------------------------------------------------------

class TestMetaTags:
    """Required meta tags are present."""

    def test_charset_meta(self):
        html = _render_struct(_make_arg_dict())
        assert 'charset=utf-8' in html.lower()

    def test_viewport_meta(self):
        html = _render_struct(_make_arg_dict())
        assert 'viewport' in html.lower()

    def test_mobile_web_app_meta(self):
        html = _render_struct(_make_arg_dict())
        assert 'mobile-web-app-capable' in html

    def test_x_ua_compatible(self):
        html = _render_struct(_make_arg_dict())
        assert 'X-UA-Compatible' in html


# ---------------------------------------------------------------------------
# Tests: Body structure
# ---------------------------------------------------------------------------

class TestBodyStructure:
    """Body contains the required GenroPy mount points."""

    def test_mainwindow_div(self):
        html = _render_struct(_make_arg_dict())
        assert 'id="mainWindow"' in html

    def test_mainwindow_has_waiting_class(self):
        html = _render_struct(_make_arg_dict())
        assert re.search(r'id="mainWindow"[^>]*class="waiting"', html)

    def test_pdb_root_div(self):
        html = _render_struct(_make_arg_dict())
        assert 'id="pdb_root"' in html

    def test_protection_shield_div(self):
        html = _render_struct(_make_arg_dict())
        assert 'id="protection_shield"' in html

    def test_body_class(self):
        html = _render_struct(_make_arg_dict(bodyclasses='mimi tundra gnr_dojotheme'))
        assert 'mimi tundra gnr_dojotheme' in html


# ---------------------------------------------------------------------------
# Tests: Scripts
# ---------------------------------------------------------------------------

class TestScripts:
    """All required scripts are present with correct attributes."""

    def test_dojo_script_src(self):
        html = _render_struct(_make_arg_dict())
        assert 'src="/_rsrc/gnr_d11/lib/dojo/dojo.js"' in html

    def test_dojo_djconfig(self):
        html = _render_struct(_make_arg_dict())
        assert 'djConfig="parseOnLoad: false"' in html

    def test_module_path_registration(self):
        html = _render_struct(_make_arg_dict())
        assert "dojo.registerModulePath('gnr','/_rsrc/gnr_d11');" in html

    def test_genro_js_imports(self):
        html = _render_struct(_make_arg_dict())
        assert 'src="/_rsrc/gnr_d11/js/genro.js"' in html
        assert 'src="/_rsrc/gnr_d11/js/genro_rpc.js"' in html

    def test_js_requires(self):
        html = _render_struct(_make_arg_dict())
        assert 'src="/_rsrc/common/public.js"' in html

    def test_genro_client_bootstrap(self):
        html = _render_struct(_make_arg_dict())
        assert 'gnr.GenroClient' in html
        assert "page_id:'test_page_001'" in html

    def test_genro_client_has_base_url(self):
        html = _render_struct(_make_arg_dict())
        assert "baseUrl:'/'" in html

    def test_genro_client_has_page_module(self):
        html = _render_struct(_make_arg_dict())
        assert "pageModule:'/path/to/index.py'" in html


# ---------------------------------------------------------------------------
# Tests: CSS
# ---------------------------------------------------------------------------

class TestCSS:
    """CSS imports and inline styles are present."""

    def test_dojo_css(self):
        html = _render_struct(_make_arg_dict())
        assert '/_rsrc/gnr_d11/lib/dojo/resources/dojo.css' in html

    def test_genro_css(self):
        html = _render_struct(_make_arg_dict())
        assert '/_rsrc/gnr_d11/css/genro.css' in html

    def test_css_requires(self):
        html = _render_struct(_make_arg_dict())
        assert '/_rsrc/common/public.css' in html

    def test_css_media_print(self):
        html = _render_struct(_make_arg_dict())
        assert '/_rsrc/gnr_d11/css/gnrprint.css' in html
        assert 'media="print"' in html

    def test_localcss_style(self):
        html = _render_struct(_make_arg_dict())
        assert 'title="localcss"' in html
        assert '#mainWindow' in html
        assert 'overflow' in html


# ---------------------------------------------------------------------------
# Tests: Optional features
# ---------------------------------------------------------------------------

class TestOptionalFeatures:
    """Optional features render correctly when enabled/disabled."""

    def test_no_pwa_when_disabled(self):
        html = _render_struct(_make_arg_dict(pwa=False))
        assert '_pwa_manifest' not in html

    def test_pwa_when_enabled(self):
        html = _render_struct(_make_arg_dict(pwa=True))
        assert '_pwa_manifest' in html
        assert 'pwa/app.js' in html

    def test_no_sentry_when_disabled(self):
        html = _render_struct(_make_arg_dict(sentryjs=None))
        assert 'sentryOnLoad' not in html

    def test_sentry_when_enabled(self):
        html = _render_struct(_make_arg_dict(
            sentryjs='https://cdn.sentry.io/sentry.js'))
        assert 'sentryOnLoad' in html
        assert 'src="https://cdn.sentry.io/sentry.js"' in html

    def test_no_favicon_when_none(self):
        html = _render_struct(_make_arg_dict(favicon=None))
        assert 'rel="icon"' not in html

    def test_favicon_when_set(self):
        html = _render_struct(_make_arg_dict(favicon='/static/favicon.ico'))
        assert '/static/favicon.ico' in html
        assert 'rel="icon"' in html

    def test_no_google_fonts_when_none(self):
        html = _render_struct(_make_arg_dict(google_fonts=None))
        assert 'fonts.googleapis.com' not in html

    def test_google_fonts_when_set(self):
        html = _render_struct(_make_arg_dict(google_fonts='Roboto'))
        assert 'fonts.googleapis.com/css?family=Roboto' in html

    def test_logo_url_when_set(self):
        html = _render_struct(_make_arg_dict(logo_url='/static/logo.png'))
        assert '--client-logo' in html
        assert '/static/logo.png' in html

    def test_dijit_imports(self):
        html = _render_struct(_make_arg_dict(
            dijitImport=['/dijit/a.js', '/dijit/b.js']))
        assert 'src="/dijit/a.js"' in html
        assert 'src="/dijit/b.js"' in html

    def test_custom_headers(self):
        custom = '<link rel="preconnect" href="https://example.com">'
        html = _render_struct(_make_arg_dict(customHeaders=[custom]))
        assert 'example.com' in html


# ---------------------------------------------------------------------------
# Tests: Comments
# ---------------------------------------------------------------------------

class TestComments:
    """HTML comments are preserved in the output."""

    def test_genropy_headers_comment(self):
        html = _render_struct(_make_arg_dict())
        assert '<!-- ================  Genropy Headers ================ -->' in html

    def test_viewport_comment(self):
        html = _render_struct(_make_arg_dict())
        assert '<!-- Prevent iPad/iPhone resize' in html


# ---------------------------------------------------------------------------
# Tests: Staging cue
# ---------------------------------------------------------------------------

class TestStagingCue:
    """The staging wrapper marks the top-level browser window when the
    site is configured with ``staging_colour`` or ``staging_style``."""

    def test_no_wrapper_when_no_staging(self):
        html = _render_struct(_make_arg_dict())
        assert 'stagingFrame' not in html

    def test_wrapper_emitted_with_staging_colour(self):
        html = _render_struct(_make_arg_dict(staging_colour='#ff8800'))
        assert 'id="stagingFrame"' in html
        assert 'background: #ff8800' in html

    def test_wrapper_emitted_with_raw_staging_style(self):
        html = _render_struct(_make_arg_dict(
            staging_style='border: 8px dashed red'))
        assert 'id="stagingFrame"' in html
        assert 'border: 8px dashed red' in html

    def test_raw_style_wins_over_colour(self):
        html = _render_struct(_make_arg_dict(
            staging_style='border: 4px solid blue',
            staging_colour='#ff8800'))
        assert 'border: 4px solid blue' in html
        assert '#ff8800' not in html

    def test_mainwindow_inside_wrapper_when_staging(self):
        html = _render_struct(_make_arg_dict(staging_colour='#ff8800'))
        idx_staging = html.find('id="stagingFrame"')
        idx_main = html.find('id="mainWindow"')
        assert 0 < idx_staging < idx_main

    def test_no_wrapper_in_subframe_even_with_staging(self):
        """The cue is meant for the top-level window only: subpages
        rendered inside an iframe must not draw their own wrapper."""
        html = _render_struct(_make_arg_dict(
            staging_colour='#ff8800', is_subframe=True))
        assert 'stagingFrame' not in html
        assert 'background: #ff8800' not in html

    def test_extra_css_rule_only_when_staging(self):
        html_off = _render_struct(_make_arg_dict())
        html_on = _render_struct(_make_arg_dict(staging_colour='#ff8800'))
        assert '#stagingFrame' not in html_off
        assert '#stagingFrame' in html_on
