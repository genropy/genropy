#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-
#
#  mako.py
#
#  Created by Giovanni Porcari on 2007-03-24.
#  Copyright (c) 2007 Softwell. All rights reserved.

# --------------------------- GnrWebPage subclass ---------------------------
import itertools
import os

from mako.lookup import TemplateLookup

from gnr.web.gnrwebpage_plugin.gnrbaseplugin import GnrBasePlugin
from gnr.web.gnrwsgisite import HTTPException
from gnr.web.gnrwebpage_proxy.frontend.template_lookup import lookup_template_class

AUTH_OK = 0
AUTH_NOT_LOGGED = 1
AUTH_FORBIDDEN = -1

class Plugin(GnrBasePlugin):
    def __call__(self, *args, **kwargs):
        dojo_theme=kwargs.pop('dojo_theme',None)
        striped=kwargs.pop('striped','odd_row,even_row')
        pdf=kwargs.pop('pdf',False)
        mako_path=kwargs.get('mako_path')
        page = self.page
        dojo_theme = dojo_theme or getattr(self.page, 'dojo_theme', None) or 'tundra'
        auth = page._checkAuth()
        if auth != AUTH_OK:
            return self.page.site.forbidden_exception
        if striped:
            kwargs['striped'] = itertools.cycle(striped.split(','))
        gnr_static_handler = page.site.getStatic('gnr')
        tpldirectories = [os.path.dirname(mako_path), page.parentdirpath] + page.resourceDirs + [
                gnr_static_handler.path(page.gnrjsversion, 'tpl')]
        page.charset = 'utf-8'
        _resources = list(page.site.resources.keys())
        _resources.reverse()

        arg_dict = page.build_arg_dict()
        arg_dict['mainpage'] = page
        arg_dict.update(kwargs)

        # When the no_mako preference is on, look for a struct template
        # next to the requested .tpl. Falls through to Mako otherwise.
        if page.getPreference('experimental.no_mako', pkg='sys'):
            tpl_basename = os.path.basename(mako_path)
            tpl_name = tpl_basename[:-4] if tpl_basename.endswith('.tpl') else tpl_basename
            template_cls = lookup_template_class(tpldirectories, tpl_name)
            if template_cls is not None:
                instance = template_cls(page)
                if not instance.check_access():
                    return self.page.site.forbidden_exception
                output = instance.render(arg_dict)
                if not pdf:
                    page.response.content_type = 'text/html'
                    return output

        lookup = TemplateLookup(directories=tpldirectories,
                                output_encoding='utf-8', encoding_errors='replace')
        template = lookup.get_template(os.path.basename(mako_path))
        try:
            output = template.render(**arg_dict)
        except HTTPException as exc:
            return exc
        if not pdf:
            page.response.content_type = 'text/html'
            return output
        else:
            pass
            ## call wkpdf executable
            #from gnr.pdf.wk2pdf import WK2pdf
            #
            #page.response.content_type = 'application/pdf'
            #tmp_name = page.temporaryDocument('tmp.pdf')
            #if page.request.query_string:
            #    query_string = '&'.join([q for q in page.query_string.split('&') if not 'pdf' in q.lower()])
            #    url = '%s?%s' % (page.path_url, query_string)
            #else:
            #    url = page.path_url
            #wkprinter = WK2pdf(url, tmp_name)
            #wkprinter.run()
            #wkprinter.exec_()
            #page.response.add_header("Content-Disposition",
            #                         str("%s; filename=%s.pdf" % ('inline', page.path_url.split('/')[-1] + '.pdf')))
            #tmp_file = open(tmp_name)
            #tmp_content = tmp_file.read()
            #tmp_file.close()
            #return tmp_content
