# -*- coding: utf-8 -*-
"""Python equivalent of ``gnr_header_static.tpl``.

Sub-template used by static-print pages (``standard_print``,
``standard_print_table``) to inject just the CSS imports (no JS,
no GenroClient bootstrap, no dojo loader).
"""

from gnr.web.gnrwebpage_proxy.frontend.basepagetemplate import BasePageTemplate


class HeaderStaticTemplate(BasePageTemplate):

    def render_into(self, builder, arg_dict):
        head = builder.head

        css_dojo = arg_dict.get('css_dojo') or []
        if css_dojo:
            head.child('style', content=self._imports(css_dojo), _type='text/css')

        for media, urls in (arg_dict.get('css_genro') or {}).items():
            if urls:
                head.child('style', content=self._imports(urls),
                           _type='text/css', media=media)

        css_requires = arg_dict.get('css_requires') or []
        if css_requires:
            head.child('style', content=self._imports(css_requires),
                       _type='text/css')

        for media, urls in (arg_dict.get('css_media_requires') or {}).items():
            if urls:
                head.child('style', content=self._imports(urls),
                           _type='text/css', media=media)

    def _imports(self, urls):
        return '\n'.join('@import url("%s");' % u for u in urls)
