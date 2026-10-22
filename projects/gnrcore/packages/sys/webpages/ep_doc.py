# -*- coding: utf-8 -*-
import json
import re
from html import escape
from urllib.parse import urlencode

from werkzeug.exceptions import Forbidden, NotFound
from werkzeug.wrappers import Response

from gnr.core.gnrstring import templateReplace
from gnr.web.gnrdocumentation import (DocumentationConflict, DocumentationStore,
                                      doc_folder, render_markdown)
from gnr.web.gnrwebpage import GnrUserNotAllowed


class GnrCustomWebPage(object):
    """The docs of the `documentation` storage (gnr.web.gnrdocumentation), for a
    registered calling page of a logged user (`_calling_page_id`); writing needs
    the documenter tags `_DOC_,doc_<pkg>` of the doc's package.

    address                      the doc as a page of its own
    address, _fragment           {exists, editable, title, html, markdown, language, mtime}
    address, asset               an image of the doc
    _index, addresses            {docs: {address: {language, mtime}}, editable: [address]}
    POST _save, address, markdown, title, base_mtime, force
                                 writes the doc; 409 when it changed since base_mtime
    POST _asset, address, dataUrl
                                 stores an image next to the doc: {link}
    """
    py_requires = 'gnrcomponents/externalcall:EndpointPermission'
    convert_result = False
    skip_connection = False

    def rootPage(self, *args, address=None, language=None, **kwargs):
        store = DocumentationStore(self.site)
        languages = [language or self.language, self.db.default_language, 'en']
        try:
            page_item = self.checkEndpointPermission(**kwargs)
            if kwargs.get('_index'):
                return self.doc_index(store, (kwargs.pop('addresses', None) or '').split(','), languages, **kwargs)
            doc_folder(address)
            if kwargs.get('_save') or kwargs.get('_asset'):
                if self.request.method != 'POST':
                    return NotFound()
                self.checkEndpointPermission(tags=self.documenterTags(address), **kwargs)
                if kwargs.get('_asset'):
                    return self._json(dict(link=store.save_asset(address, kwargs.get('dataUrl'))))
                return self.doc_save(store, address, languages[0], page_item['user'], **kwargs)
            if kwargs.get('asset'):
                return self.doc_asset(store, address, kwargs['asset'])
            return self.doc_read(store, address, languages, **kwargs)
        except GnrUserNotAllowed:
            return Forbidden()
        except ValueError:
            return NotFound()

    def documenterTags(self, address):
        return '_DOC_,doc_%s' % doc_folder(address).split('/')[0]

    def isDocumenter(self, address, **kwargs):
        try:
            self.checkEndpointPermission(tags=self.documenterTags(address), **kwargs)
        except GnrUserNotAllowed:
            return False
        return True

    def docUrl(self, address, **kwargs):
        return '/sys/ep_doc?%s' % urlencode(dict(address=address, **kwargs))

    def _json(self, data):
        self.response.content_type = 'application/json'
        return json.dumps(data)

    def doc_index(self, store, addresses, languages, **kwargs):
        allowed = {}
        editable = []
        for address in addresses:
            try:
                pkg = doc_folder(address).split('/')[0]
            except ValueError:
                continue
            if pkg not in allowed:
                allowed[pkg] = self.isDocumenter(address, **kwargs)
            if allowed[pkg]:
                editable.append(address)
        return self._json(dict(docs=store.index(addresses, languages), editable=editable))

    def doc_read(self, store, address, languages, _fragment=None, **kwargs):
        doc = store.read(address, languages)
        page_id = kwargs.get('_calling_page_id') or kwargs.get('_current_page_id')
        title = (doc['meta'].get('title') if doc else None) or address.split(':')[-1] or address
        html = render_markdown(doc['markdown'], lambda name: self.docUrl(address, asset=name,
                                                                         _calling_page_id=page_id)) if doc else ''
        if not _fragment:
            if not doc:
                return NotFound()
            self.response.content_type = 'text/html'
            # out of a card nothing fills the template variables: they are blanked
            values = {name: '' for name in re.findall(r'\$([a-zA-Z0-9_]+)', html)}
            return templateReplace(self.getResourceContent(resource='ep_doc/doc_page_tpl', ext='html'),
                                   dict(title=escape(title), body=templateReplace(html, values)))
        editable = self.isDocumenter(address, _calling_page_id=page_id)
        if not (doc or editable):
            return NotFound()
        return self._json(dict(exists=bool(doc), editable=editable, title=title, html=html,
                               markdown=doc['markdown'] if doc else '',
                               language=doc['language'] if doc else languages[0],
                               mtime=doc['mtime'] if doc else None))

    def doc_save(self, store, address, language, user, markdown=None, title=None,
                 base_mtime=None, force=None, **kwargs):
        try:
            mtime = store.save(address, language, markdown or '', title=title, author=user,
                               base_mtime=float(base_mtime) if base_mtime else None,
                               force=force in ('1', 'true', True))
        except DocumentationConflict as e:
            return Response(json.dumps(dict(conflict=True, mtime=e.mtime)), status=409,
                            mimetype='application/json')
        return self._json(dict(mtime=mtime))

    def doc_asset(self, store, address, name):
        node = store.asset_node(address, name)
        if not node.exists:
            return NotFound()
        self.response.content_type = node.mimetype
        with node.open('rb') as f:
            return f.read()
