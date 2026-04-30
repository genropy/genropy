# -*- coding: utf-8 -*-
"""Struct-based equivalent of ``gnr_header.tpl``.

Populates the ``<head>`` block with the GenroPy bootstrap: dojo loader,
optional integrations (PWA, Sentry, favicon, Google Fonts), framework
JS / CSS, page-specific requires, and the inline ``<script>`` that
instantiates ``new gnr.GenroClient(...)``.

Used as a sub-template by :class:`standard.PageTemplate` via
:meth:`HeaderTemplate.render_into`.
"""

from gnr.web.gnrwebpage_proxy.frontend.basepagetemplate import BasePageTemplate


class HeaderTemplate(BasePageTemplate):

    def render_into(self, builder, arg_dict):
        """Append GenroPy header content to ``builder.head`` and emit the
        bootstrap ``<script>`` at the end of ``builder.body``.

        The body-level script call mirrors the original ``gnr_header.tpl``
        which ends with ``new gnr.GenroClient(...)`` outside of <head>.
        """
        head = builder.head
        body = builder.body

        head.script(_src=arg_dict.get('dojolib', ''),
                    djConfig=arg_dict.get('djConfig', ''))
        head.script("dojo.registerModulePath('gnr','%s');"
                    % arg_dict.get('gnrModulePath', ''))

        if arg_dict.get('pwa'):
            head.link(rel='manifest', crossorigin='use-credentials',
                      href='/_pwa_manifest.json')
            head.script(_src='/_rsrc/common/pwa/app.js')

        if arg_dict.get('sentryjs'):
            head.script(self._sentry_init_snippet(arg_dict))
            head.script(_src=arg_dict['sentryjs'], crossorigin='anonymous')

        favicon = arg_dict.get('favicon')
        if favicon:
            head.link(rel='icon', href=favicon)
            head.link(rel='apple-touch-icon', href=favicon)

        google_fonts = arg_dict.get('google_fonts')
        if google_fonts:
            head.link(rel='stylesheet', _type='text/css',
                      href='http://fonts.googleapis.com/css?family=%s' % google_fonts)

        for src in arg_dict.get('dijitImport') or []:
            head.script(_src=src)

        for src in arg_dict.get('genroJsImport') or []:
            head.script(_src=src)

        for raw in arg_dict.get('customHeaders') or []:
            head.child(tag='__flatten__', content=raw)

        for src in arg_dict.get('js_requires') or []:
            head.script(_src=src)

        logo_url = arg_dict.get('logo_url')
        if logo_url:
            head.style(':root { --client-logo: transparent url(%s) no-repeat center center; }'
                       % logo_url)

        css_dojo = arg_dict.get('css_dojo') or []
        if css_dojo:
            head.style(self._css_imports(css_dojo))

        for media, urls in (arg_dict.get('css_genro') or {}).items():
            if urls:
                head.style(self._css_imports(urls), media=media)

        css_requires = arg_dict.get('css_requires') or []
        if css_requires:
            head.style(self._css_imports(css_requires))

        for media, urls in (arg_dict.get('css_media_requires') or {}).items():
            if urls:
                head.style(self._css_imports(urls), media=media)

        body.script(self._client_bootstrap(arg_dict))

    def _css_imports(self, urls):
        return '\n'.join('@import url("%s");' % u for u in urls)

    def _sentry_init_snippet(self, arg_dict):
        return (
            "window.sentryOnLoad = function() {"
            "console.log('GENROPY SENTRY SUPPORT INIT');"
            "Sentry.init({"
            "sampleRate: %s,"
            "traceSampleRate: %s,"
            "profilesSampleRate: %s,"
            "replaysSessionSampleRate: %s,"
            "replaysOnErrorSampleRate: %s"
            "});"
            "Sentry.addEventProcessor(event => {"
            "try {"
            "event.tags = {"
            "gnr_package: genro.getData('gnr.package'),"
            "genropy_instance: genro.getData('gnr.siteName'),"
            "genro_loaded: true,"
            "gnr_table: genro.getData('gnr.table'),"
            "gnr_pagename: genro.getData('gnr.pagename'),"
            "gnr_page_id: genro.getData('gnr.page_id')"
            "};"
            "Sentry.setUser({\"username\": genro.getData('gnr.avatar.user')});"
            "} catch (error) {"
            "Sentry.setTag('genro_loaded', false);"
            "}"
            "return event;"
            "});"
            "};"
        ) % (
            arg_dict.get('sentry_sample_rate', '0.0'),
            arg_dict.get('sentry_traces_sample_rate', '0.0'),
            arg_dict.get('sentry_profiles_sample_rate', '0.0'),
            arg_dict.get('sentry_replays_session_sample_rate', '0.0'),
            arg_dict.get('sentry_replays_on_error_sample_rate', '0.0'),
        )

    def _client_bootstrap(self, arg_dict):
        return (
            "var genro = new gnr.GenroClient({"
            "page_id:'%s',"
            "baseUrl:'%s',"
            "pageMode:'%s',"
            "pageModule:'%s',"
            "domRootName:'mainWindow',"
            "startArgs:%s"
            "});"
        ) % (
            arg_dict.get('page_id', ''),
            arg_dict.get('baseUrl', '/'),
            arg_dict.get('pageMode', 'legacy'),
            arg_dict.get('pageModule', ''),
            arg_dict.get('startArgs', '{}'),
        )
