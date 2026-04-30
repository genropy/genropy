# -*- coding: utf-8 -*-
"""Python equivalent of ``standard.tpl`` for GenroPy rootPage.

Activated via ``experimental.no_mako`` preference. The Mako file
``gnrjs/gnr_d{11,20}/tpl/standard.tpl`` remains as fallback.
"""

from gnr.web.gnrwebpage_proxy.frontend.basepagetemplate import BasePageTemplate
from gnr.web.gnrwebpage_proxy.frontend.template_lookup import lookup_template_class


class PageTemplate(BasePageTemplate):

    def build(self, builder, arg_dict):
        head = builder.head
        body = builder.body
        charset = arg_dict.get('charset', 'utf-8')

        head.child('meta', _attributes={'http-equiv': 'content-type'},
                   _content='text/html; charset=%s' % charset)
        head.child('meta', _attributes={'http-equiv': 'X-UA-Compatible'},
                   _content='chrome=1')
        head.comment('Prevent iPad/iPhone resize and enable full screen mode'
                     ' (if you bookmark the app on the home screen)')
        head.child('meta', name='mobile-web-app-capable', _content='yes')
        head.child('meta', name='apple-mobile-web-app-status-bar-style',
                   _content='black')
        head.child('meta', name='viewport',
                   _content='user-scalable=no, width=device-width,'
                            ' initial-scale=1, maximum-scale=1')
        head.child('link', rel='apple-touch-icon',
                   href='_rsrc/mobile/ios/images/app_icon.png')
        head.child('link', rel='apple-touch-startup-image',
                   href='_rsrc/mobile/ios/images/startup_image.jpg')

        header_cls = lookup_template_class(
            self.page.tpldirectories, 'gnr_header', symbol='HeaderTemplate'
        )
        if header_cls is not None:
            header_cls(self.page).render_into(builder, arg_dict)

        staging_style = self._resolve_staging_style(arg_dict)

        if staging_style:
            css_parts = [
                'html, body{width: 100%;height: 100%; overflow:hidden;}',
                '#stagingFrame{position: relative;'
                ' width: 100%; height: 100%; overflow: hidden;}',
                '#stagingFrame #mainWindow{position: absolute;'
                ' top: 6px; right: 6px; bottom: 6px; left: 6px;'
                ' overflow: hidden;}',
            ]
        else:
            css_parts = ['html, body, #mainWindow'
                         '{width: 100%;height: 100%; overflow:hidden;}']
        head.child('style', content=' '.join(css_parts),
                   _type='text/css', title='localcss')

        body.attributes['class'] = arg_dict.get('bodyclasses', '')
        if staging_style:
            staging = body.child('div', id='stagingFrame', style=staging_style)
            staging.child('div', id='mainWindow', _class='waiting')
        else:
            body.child('div', id='mainWindow', _class='waiting')
        body.child('div', id='pdb_root')
        body.child('div', id='protection_shield')

    def _resolve_staging_style(self, arg_dict):
        """Compose the inline style for the staging wrapper, or None.

        ``staging_style`` (raw CSS) wins over ``staging_colour`` (shortcut).
        The wrapper is also suppressed when the page is rendered inside
        another page's iframe (``is_subframe``): the cue is meant to mark
        the top-level browser window, not the embedded subpages.

        Returns None when no wrapper should be emitted; in that case the
        layout matches the non-staging case."""
        if arg_dict.get('is_subframe'):
            return None
        style = arg_dict.get('staging_style')
        if style:
            return style
        colour = arg_dict.get('staging_colour')
        if colour:
            return 'background: %s' % colour
        return None
