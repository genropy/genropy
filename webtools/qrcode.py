#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-
#
#  untitled
#
#  Created by Giovanni Porcari on 2007-03-24.
#  Copyright (c) 2007 Softwell. All rights reserved.
#

# --------------------------- BaseWebtool subclass ---------------------------


from gnr.web.gnrbaseclasses import BaseWebtool
import qrcode
import qrcode.image.svg


class QRCode(BaseWebtool):
    def __call__(self, text=None,**kwargs):
        qr = qrcode.QRCode(image_factory=qrcode.image.svg.SvgPathImage)
        qr.add_data(text)
        #qr.make(fit=True)
        img = qr.make_image(attrib={'style': 'width:100%;height:100%;'})
        self.content_type = 'text/html'
        return f"<div style='position:absolute;top:0;left:0;right:0;bottom:0;overflow:hidden;'>{img.to_string(encoding='unicode')}</div>"