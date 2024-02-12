#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-
#
#  Created by Saverio Porcari on 2013-04-06.
#  Copyright (c) 2013 Softwell. All rights reserved.


from __future__ import division
from __future__ import print_function
from past.utils import old_div
from gnr.lib.services import GnrBaseService                                                  
import urllib.request, urllib.error, urllib.parse
import os


class Main(GnrBaseService):
    def __init__(self,parent,**kwargs):
        self.parent = parent

    def __call__(self,url,destinationFolder=None,filename=None,filepath=None):
        u = urllib.request.urlopen(url)
        if filepath:
            destinationFolder,filename = os.path.split(filepath)
        else:
            filename = filename or url.split('/')[-1]
            destinationFolder = destinationFolder or 'site:download'
            if ':' in destinationFolder:
                filepath = self.parent.getStaticPath(destinationFolder,filename)
            else:
                filepath = os.path.join(destinationFolder,filename)
        if not os.path.isdir(destinationFolder):
            os.makedirs(destinationFolder)
        with open(os.path.join(filepath), 'wb') as f:
            meta = u.info()
            file_size = int(meta.getheaders("Content-Length")[0])
            print("Downloading: %s Bytes: %s" % (filename, file_size))
            file_size_dl = 0
            block_sz = 8192
            while True:
                buffer = u.read(block_sz)
                if not buffer:
                    break
                file_size_dl += len(buffer)
                f.write(buffer)
                status = r"%10d  [%3.2f%%]" % (file_size_dl, old_div(file_size_dl * 100., file_size))
                status = status + chr(8)*(len(status)+1)
                print(status, end=' ')
            f.close()
        return filepath