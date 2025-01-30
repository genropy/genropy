#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-
#
#  jstools.py
#
#  Created by Giovanni Porcari on 2007-03-24.
#  Copyright (c) 2007 Softwell. All rights reserved.

import os
import hashlib
import tempfile
import shutil
        
from gnr.web.gnrwebpage_proxy.gnrbaseproxy import GnrBaseProxy
from jsmin import jsmin

class GnrWebJSTools(GnrBaseProxy):
    def init(self, **kwargs):
        pass

    def jsmin(self, js):
        return jsmin(js)

    def compress(self, jsfiles):
        return self.compress_js(jsfiles)
        
    def compress_js(self, jsfiles):
        site = self.page.site
        ts = str(max([os.path.getmtime(fname) for fname in jsfiles]))
        key = '-'.join(jsfiles)
        cpfile = '%s.js' % hashlib.md5((key + ts).encode()).hexdigest()
        jspath = site.getStatic('site').path('_static', '_jslib', cpfile)
        jsurl = site.getStatic('site').url('_static', '_jslib', cpfile)
        rebuild = True
        if os.path.isfile(jspath):
            rebuild = False
        if rebuild:
            path = site.getStatic('site').path('_static', '_jslib')
            if not os.path.exists(path):
                os.makedirs(path)
                
            outfile_handle, outfile_path = tempfile.mkstemp(prefix='gnrcompress',suffix='.js')
            with os.fdopen(outfile_handle, "w") as cpf:
                cpf.write('// %s\n' % ts)
                for fname in jsfiles:
                    with open(fname) as f:
                        js = f.read()
                    cpf.write(jsmin(js, quote_chars="'\"`"))
                    cpf.write('\n\n\n\n')
                cpf.flush()
                os.fsync(cpf.fileno())
            shutil.move(outfile_path, jspath)
        return jsurl
