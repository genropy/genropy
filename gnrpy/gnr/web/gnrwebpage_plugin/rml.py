#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-
#
#  rml.py
#
#  Created by Giovanni Porcari on 2007-03-24.
#  Copyright (c) 2007 Softwell. All rights reserved.

# --------------------------- GnrWebPage subclass ---------------------------

import os.path
from .mako.lookup import TemplateLookup
from gnr.web.gnrwebpage import AUTH_OK
from gnr.web.gnrwebpage_plugin.gnrbaseplugin import GnrBasePlugin
from gnr.web.gnrwebpage_proxy.frontend.template_lookup import lookup_template_class



class Plugin(GnrBasePlugin):
    def __call__(self, path, inline=False, **kwargs):
        auth = self._checkAuth()
        if auth != AUTH_OK:
            self.raiseUnauthorized()
        tpldirectories = [os.path.dirname(path), self.parentdirpath] + self.resourceDirs + [
                self.resolvePath('gnrjs', 'gnr_d%s' % self.dojo_version, 'tpl', folder='*lib')]
        self.response.content_type = 'application/pdf'
        filename = os.path.split(path)[-1].split('.')[0]
        inline_attr = (inline and 'inline') or 'attachment'
        self.response.add_header("Content-Disposition", str("%s; filename=%s.pdf" % (inline_attr, filename)))
        import io
        from lxml import etree
        from z3c.rml import document

        tmp = None
        # When no_mako preference is on, try a struct template first.
        if self.getPreference('experimental.no_mako', pkg='sys'):
            tpl_basename = os.path.basename(path)
            for ext in ('.rml', '.tpl'):
                if tpl_basename.endswith(ext):
                    tpl_name = tpl_basename[:-len(ext)]
                    break
            else:
                tpl_name = tpl_basename
            template_cls = lookup_template_class(tpldirectories, tpl_name)
            if template_cls is not None:
                instance = template_cls(self)
                if not instance.check_access():
                    self.raiseUnauthorized()
                tmp = instance.render(dict(kwargs, mainpage=self))

        if tmp is None:
            lookup = TemplateLookup(directories=tpldirectories,
                                    output_encoding='utf-8', encoding_errors='replace')
            template = lookup.get_template(os.path.basename(path))
            tmp = template.render(mainpage=self, **kwargs)

        tmp = tmp.replace('&', '&amp;')
        root = etree.fromstring(tmp)
        doc = document.Document(root)
        output = io.StringIO()
        doc.process(output)
        output.seek(0)
        return output.read()
