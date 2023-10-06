#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-

from gnr.lib.services.storage import StorageService
from gnr.web.gnrbaseclasses import BaseComponent
import os
import tempfile
import stat
from gnr.core.gnrlang import getUuid
import urllib.request
from mimetypes import guess_extension

class HttpTemporaryFilename(object):
    def __init__(self, url=None, keep=False):
        self.url = url
        self.keep = keep

    def __enter__(self):
        ext = None
        with urllib.request.urlopen(self.url) as response:
            response_code = response.code
            if response_code==200:
                ext = guess_extension(response.headers['content-type'].partition(';')[0].strip())
            self.fd,self.name = tempfile.mkstemp(suffix=ext)
            if response_code==200:
                with os.fdopen(self.fd, 'wb') as f:
                    f.write(response.read())
            self.enter_mtime = None
        return self.name

    def __exit__(self, exc, value, tb):
        if not self.keep:
            os.unlink(self.name)


class Service(StorageService):

    def expandpath(self,path):
        return path

    def serve(self, path, environ, start_response, download=False, download_name=None, **kwargs):
        return self.parent.not_found_exception(environ, start_response)

    def url(self, *args, **kwargs):
        return args[0]


    def autocreate(self, *args, **kwargs):
        """Autocreates all intermediate directories of a path"""
        pass


    @property
    def location_identifier(self):
        return getUuid()

    def internal_path(self, *args, **kwargs):
        return args[0]


    def open(self, *args, **kwargs):
        return urllib.request.urlopen(args[0])

    def exists(self, *args):
        with self.open(*args) as response:
            return response.code==200
    def local_path(self, *args, **kwargs):
        return HttpTemporaryFilename(url=args[0])

    def isdir(self, *args):
        return False

    def isfile(self, *args):
        return self.exists(*args)

    def children(self, *args, **kwargs):
        return []
