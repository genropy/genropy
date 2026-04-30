# -*- coding: utf-8 -*-
"""Struct-based equivalent of ``gnr_header_dojo.tpl``.

Sub-template that emits the dojo loader plus all CSS imports. Used
by pages that need dojo bootstrap but not the full GenroClient
init (e.g. simpler dojo-themed pages).
"""

from gnr.web.gnrwebpage_proxy.frontend.basepagetemplate import BasePageTemplate


class HeaderDojoTemplate(BasePageTemplate):

    def render_into(self, builder, arg_dict):
        head = builder.head

        head.script(_src=arg_dict.get('dojolib', ''),
                    djConfig=arg_dict.get('djConfig', ''))

        css_dojo = arg_dict.get('css_dojo') or []
        if css_dojo:
            head.style(self._imports(css_dojo))

        for media, urls in (arg_dict.get('css_genro') or {}).items():
            if urls:
                head.style(self._imports(urls), media=media)

        css_requires = arg_dict.get('css_requires') or []
        if css_requires:
            head.style(self._imports(css_requires))

        for media, urls in (arg_dict.get('css_media_requires') or {}).items():
            if urls:
                head.style(self._imports(urls), media=media)

    def _imports(self, urls):
        return '\n'.join('@import url("%s");' % u for u in urls)
