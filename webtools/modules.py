#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os

from werkzeug.wrappers import Response

from gnr.web.gnrbaseclasses import BaseWebtool

MANIFEST = 'manifest.json'


class Modules(BaseWebtool):
    """Serve the GenroApp modules signed by Softwell for this site.

    Each module lives in ``site:genroapp/modules/<name>/<version>/`` with its
    signed ``manifest.json``. ``/_tools/modules`` answers the array of the
    manifests; ``/_tools/modules/<name>/<version>/<path>`` answers the raw
    bytes of one file. Nothing is signed or changed here."""

    content_type = 'application/json'

    def __call__(self, *args, **kwargs):
        root = self.site.get_genroapp_modules_path()
        if not root:
            return self.not_found('No GenroApp modules for this site')
        if not args:
            return json.dumps(self.manifests(root))
        path = self.module_file_path(root, args)
        if not path:
            return self.not_found('Not found')
        self.content_type = 'application/octet-stream'
        with open(path, 'rb') as f:
            return f.read()

    def not_found(self, message):
        return Response(message, status=404, mimetype='text/plain')

    def manifests(self, root):
        """Return the parsed manifests of every ``<name>/<version>/`` in ``root``.

        A manifest is read only when its resolved path is
        ``<root>/<name>/<version>/manifest.json``: a symbolic link at any of
        the three levels moves it outside the tree and it is skipped."""
        result = []
        for name in sorted(os.listdir(root)):
            module_folder = os.path.join(root, name)
            if not os.path.isdir(module_folder):
                continue
            for version in sorted(os.listdir(module_folder)):
                manifest = os.path.join(module_folder, version, MANIFEST)
                if os.path.realpath(manifest) != manifest:
                    continue
                if os.path.isfile(manifest):
                    with open(manifest, encoding='utf-8') as f:
                        result.append(json.load(f))
        return result

    def module_file_path(self, root, args):
        """Return the resolved path of a package file, or ``None`` when the
        request does not name a regular file inside ``<name>/<version>/``."""
        if len(args) < 3:
            return None
        name, version, relative = args[0], args[1], args[2:]
        folder = os.path.realpath(os.path.join(root, name, version))
        if os.path.dirname(os.path.dirname(folder)) != root:
            return None
        path = os.path.realpath(os.path.join(folder, *relative))
        if not path.startswith(folder + os.sep) or path == os.path.join(folder, MANIFEST):
            return None
        return path if os.path.isfile(path) else None
