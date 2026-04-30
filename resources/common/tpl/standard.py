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

        head.child('style', content='html, body, #mainWindow'
                   '{width: 100%;height: 100%; overflow:hidden;}',
                   _type='text/css', title='localcss')

        body.attributes['class'] = arg_dict.get('bodyclasses', '')
        body.child('div', id='mainWindow', _class='waiting')
        body.child('div', id='pdb_root')
        body.child('div', id='protection_shield')
