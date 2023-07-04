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
import tempfile
import mimetypes
import urllib

import qrcode.image.svg


class QRCode(BaseWebtool):
    def __call__(self, text=None,url=None,mode='png',**kwargs):
        if url:
            text = urllib.parse.unquote(url)
        return getattr(self,f'qrcode_{mode}')(text)

    def qrcode_png(self,text=None):
        img = qrcode.make(text)
        type(img)  # qrcode.image.pil.PilImage
        suffix = '.png'
        temp = tempfile.NamedTemporaryFile(suffix=suffix)
        self.content_type = mimetypes.guess_type(temp.name)[0]
        img.save(temp, format=suffix[1:])
        temp.seek(0)
        result = temp.read()
        temp.close()
        return result
    
    def qrcode_svg(self,text=None):
        qr = qrcode.QRCode(image_factory=qrcode.image.svg.SvgPathImage)
        qr.add_data(text)
        #qr.make(fit=True)
        img = qr.make_image(attrib={'style': 'width:100%;height:100%;'})
        self.content_type = 'text/html'
        return f"<div style='position:absolute;top:0;left:0;right:0;bottom:0;overflow:hidden;'>{img.to_string(encoding='unicode')}</div>"