# -*- coding: utf-8 -*-
"""Python equivalent of ``gnr_header.tpl``.

Populates the ``<head>`` with the GenroPy bootstrap: dojo loader,
optional integrations, framework JS/CSS, and the GenroClient init script.
"""

from gnr.web.gnrwebpage_proxy.frontend.basepagetemplate import BasePageTemplate


class HeaderTemplate(BasePageTemplate):

    def render_into(self, builder, arg_dict):
        head = builder.head

        head.comment('================  Genropy Headers ================')
        head.child('script', content=' ', src=arg_dict.get('dojolib', ''),
                   djConfig=arg_dict.get('djConfig', ''), _type='text/javascript')
        head.child('script', content="dojo.registerModulePath('gnr','%s');"
                   % arg_dict.get('gnrModulePath', ''), _type='text/javascript')

        if arg_dict.get('pwa'):
            head.child('link', rel='manifest', crossorigin='use-credentials',
                       href='/_pwa_manifest.json')
            head.child('script', content='', src='/_rsrc/common/pwa/app.js',
                       _type='text/javascript')

        if arg_dict.get('sentryjs'):
            head.child('script', content=self._sentry_init_snippet(arg_dict),
                       _type='text/javascript')
            head.child('script', content='', src=arg_dict['sentryjs'],
                       crossorigin='anonymous')

        favicon = arg_dict.get('favicon')
        if favicon:
            head.child('link', rel='icon', href=favicon)
            head.child('link', rel='apple-touch-icon', href=favicon)

        google_fonts = arg_dict.get('google_fonts')
        if google_fonts:
            head.child('link', rel='stylesheet', _type='text/css',
                       href='http://fonts.googleapis.com/css?family=%s' % google_fonts)

        for src in arg_dict.get('dijitImport') or []:
            head.child('script', content='', src=src, _type='text/javascript')

        for src in arg_dict.get('genroJsImport') or []:
            head.child('script', content='', src=src, _type='text/javascript')

        for raw in arg_dict.get('customHeaders') or []:
            head.child(tag='__flatten__', content=raw)

        for src in arg_dict.get('js_requires') or []:
            head.child('script', content='', src=src, _type='text/javascript')

        logo_url = arg_dict.get('logo_url')
        if logo_url:
            head.child('style',
                       content=':root { --client-logo: transparent url(%s)'
                               ' no-repeat center center; }' % logo_url,
                       _type='text/css')

        css_dojo = arg_dict.get('css_dojo') or []
        if css_dojo:
            head.child('style', content=self._css_imports(css_dojo),
                       _type='text/css')

        for cssmedia, cssnames in (arg_dict.get('css_genro') or {}).items():
            if cssnames:
                head.child('style', content=self._css_imports(cssnames),
                           _type='text/css', media=cssmedia)

        css_requires = arg_dict.get('css_requires') or []
        if css_requires:
            head.child('style', content=self._css_imports(css_requires),
                       _type='text/css')

        for cssmedia, cssnames in (arg_dict.get('css_media_requires') or {}).items():
            if cssnames:
                head.child('style', content=self._css_imports(cssnames),
                           _type='text/css', media=cssmedia)

        head.child('script', content=self._client_bootstrap(arg_dict),
                   _type='text/javascript')

    def _css_imports(self, urls):
        return '\n'.join('@import url("%s");' % u for u in urls)

    def _sentry_init_snippet(self, arg_dict):
        return (
            "window.sentryOnLoad = function() {\n"
            '  console.log("GENROPY SENTRY SUPPORT INIT");\n'
            "  Sentry.init({\n"
            "    sampleRate: %(sentry_sample_rate)s,\n"
            "    traceSampleRate: %(sentry_traces_sample_rate)s,\n"
            "    profilesSampleRate: %(sentry_profiles_sample_rate)s,\n"
            "    replaysSessionSampleRate: %(sentry_replays_session_sample_rate)s,\n"
            "    replaysOnErrorSampleRate: %(sentry_replays_on_error_sample_rate)s\n"
            "  });\n"
            "  Sentry.addEventProcessor(event => {\n"
            "    try {\n"
            "      event.tags = {\n"
            "        gnr_package: genro.getData('gnr.package'),\n"
            "        genropy_instance: genro.getData('gnr.siteName'),\n"
            "        genro_loaded: true,\n"
            "        gnr_table: genro.getData('gnr.table'),\n"
            "        gnr_pagename: genro.getData('gnr.pagename'),\n"
            "        gnr_page_id: genro.getData('gnr.page_id')\n"
            "      };\n"
            '      Sentry.setUser({"username": genro.getData(\'gnr.avatar.user\')});\n'
            "    } catch (error) {\n"
            '      Sentry.setTag("genro_loaded", false);\n'
            "    }\n"
            "    return event;\n"
            "  });\n"
            "};"
        ) % {
            'sentry_sample_rate': arg_dict.get('sentry_sample_rate', '0.0'),
            'sentry_traces_sample_rate': arg_dict.get('sentry_traces_sample_rate', '0.0'),
            'sentry_profiles_sample_rate': arg_dict.get('sentry_profiles_sample_rate', '0.0'),
            'sentry_replays_session_sample_rate': arg_dict.get('sentry_replays_session_sample_rate', '0.0'),
            'sentry_replays_on_error_sample_rate': arg_dict.get('sentry_replays_on_error_sample_rate', '0.0'),
        }

    def _client_bootstrap(self, arg_dict):
        return (
            "var genro = new gnr.GenroClient({"
            " page_id:'%(page_id)s',"
            "baseUrl:'%(filename)s',"
            " pageMode: '%(pageMode)s',"
            " pageModule:'%(pageModule)s',"
            " domRootName:'mainWindow',"
            " startArgs: %(startArgs)s,"
            " baseUrl:'%(baseUrl)s'"
            "});"
        ) % {
            'page_id': arg_dict.get('page_id', ''),
            'filename': arg_dict.get('filename', ''),
            'pageMode': arg_dict.get('pageMode', 'legacy'),
            'pageModule': arg_dict.get('pageModule', ''),
            'startArgs': arg_dict.get('startArgs', '{}'),
            'baseUrl': arg_dict.get('baseUrl', '/'),
        }
