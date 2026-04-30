# -*- coding: utf-8 -*-
"""Struct-based equivalent of ``standard.tpl`` for GenroPy rootPage.

This template is the entry point used when the preference
``experimental.no_mako`` is enabled. The Mako file
``gnrjs/gnr_d{11,20}/tpl/standard.tpl`` remains in place as fallback.

A package can override this template by providing
``<pkg>/resources/tpl/standard.py``. The resource lookup honours the
same precedence used elsewhere in GenroPy.
"""

from gnr.web.gnrwebpage_proxy.frontend.basepagetemplate import BasePageTemplate
from gnr.web.gnrwebpage_proxy.frontend.template_lookup import lookup_template_class


class PageTemplate(BasePageTemplate):
    """Render the canonical GenroPy SPA shell.

    The output is a ``<!DOCTYPE html>`` document with a ``<head>`` filled
    by :class:`HeaderTemplate` and a ``<body>`` containing the standard
    GenroPy mount points: ``#mainWindow``, ``#pdb_root``,
    ``#protection_shield``. When a staging style or colour is configured,
    ``#mainWindow`` is wrapped in a ``#stagingFrame`` div so the visual
    cue does not interfere with the geometry the dojo widgets expect.
    """

    def build(self, builder, arg_dict):
        head = builder.head
        body = builder.body

        head.meta(http_equiv='content-type',
                  content='text/html; charset=%s' % arg_dict.get('charset', 'utf-8'))
        head.meta(http_equiv='X-UA-Compatible', content='chrome=1')
        head.meta(name='mobile-web-app-capable', content='yes')
        head.meta(name='apple-mobile-web-app-status-bar-style', content='black')
        head.meta(name='viewport',
                  content='user-scalable=no, width=device-width, '
                          'initial-scale=1, maximum-scale=1')
        head.link(rel='apple-touch-icon',
                  href='_rsrc/mobile/ios/images/app_icon.png')
        head.link(rel='apple-touch-startup-image',
                  href='_rsrc/mobile/ios/images/startup_image.jpg')

        header_cls = lookup_template_class(self.page.tpldirectories,
                                           'gnr_header',
                                           symbol='HeaderTemplate')
        if header_cls is not None:
            header_cls(self.page).render_into(builder, arg_dict)

        staging_style = self._resolve_staging_style(arg_dict)

        css_lines = [
            'html, body, #mainWindow{width: 100%; height: 100%; overflow: hidden;}',
        ]
        if staging_style:
            css_lines.append(
                '#stagingFrame{box-sizing: border-box; width: 100%; height: 100%;}'
            )
        head.style(' '.join(css_lines), title='localcss')

        body.attributes['class'] = arg_dict.get('bodyclasses', '')

        if staging_style:
            staging = body.div(id='stagingFrame', style=staging_style)
            staging.div(id='mainWindow', _class='waiting')
        else:
            body.div(id='mainWindow', _class='waiting')
        body.div(id='pdb_root')
        body.div(id='protection_shield')

    def _resolve_staging_style(self, arg_dict):
        """Resolve the staging style, with raw style winning over colour.

        The wrapper ``#stagingFrame`` is emitted only when at least one
        of ``staging_style`` (raw CSS) or ``staging_colour`` (shortcut)
        is provided via env vars or siteconfig. When both are empty, no
        wrapper is emitted and the HTML matches the legacy layout
        byte-for-byte (modulo whitespace).
        """
        style = arg_dict.get('staging_style')
        if style:
            return style
        colour = arg_dict.get('staging_colour')
        if colour:
            return 'padding: 6px; background: %s' % colour
        return None
