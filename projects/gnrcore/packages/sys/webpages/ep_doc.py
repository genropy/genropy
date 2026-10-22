# -*- coding: utf-8 -*-
import json
import re
from html import escape

from werkzeug.exceptions import Forbidden, NotFound

from gnr.core.gnrstring import templateReplace
from gnr.web.gnrwebpage import GnrUserNotAllowed


class GnrCustomWebPage(object):
    """The documentation of grouplets, fields and handbook pages at one address,
    `<kind>:<target>:<name>`: grouplet:<pkg.table|pkg>:<resource>,
    help:<pkg.table>[/<resourceClass>]:<helpcode>, docu:[<table>]:<hierarchical name>.
    It answers only a registered page of a logged user (`_calling_page_id`),
    who must also own the `doc_tags` of a grouplet's card if it sets them.
    With `_fragment` the popup of that page gets {title, html} — a grouplet doc
    as its template, filled by the popup on the card's data — or {title, page}
    for a doc that is a page of its own, shown in an iframe."""
    py_requires = ('gnrcomponents/externalcall:EndpointPermission,'
                   'gnrcomponents/grouplet/grouplet:GroupletHandler')
    convert_result = False
    skip_connection = False

    def rootPage(self, *args, address=None, _fragment=None, language=None, **kwargs):
        parts = (address or '').split(':', 2)
        handler = getattr(self, f'doc_{parts[0]}', None) if len(parts) == 3 else None
        try:
            self.checkEndpointPermission(**kwargs)
            doc = handler(parts[1], parts[2], language=language or self.language) if handler else None
            if doc and doc.get('tags'):
                self.checkEndpointPermission(tags=doc['tags'], **kwargs)
        except GnrUserNotAllowed:
            return Forbidden()
        if not doc:
            return NotFound()
        if _fragment:
            self.response.content_type = 'application/json'
            if doc.get('page'):
                return json.dumps(dict(title=doc['title'], page=True))
            return json.dumps(dict(title=doc['title'], html=doc['html']))
        self.response.content_type = 'text/html'
        if doc.get('page'):
            return doc['page']
        return templateReplace(self.getResourceContent(resource='ep_doc/doc_page_tpl', ext='html'),
                               dict(title=escape(doc['title'] or ''), body=self.standaloneBody(doc)))

    def standaloneBody(self, doc):
        """Out of a card nothing fills the template: its doc_kw, then blanks"""
        if doc.get('doc_kw') is None:
            return doc['html']
        values = {name: '' for name in re.findall(r'\$([a-zA-Z0-9_]+)', doc['html'])}
        values.update(doc['doc_kw'])
        return templateReplace(doc['html'], values)

    def doc_grouplet(self, target, resource, language=None):
        table, pkg = (target, None) if '.' in target else (None, target)
        info, abs_path = self._gr_resourceInfo(resource=resource, table=table, pkg=pkg)
        card = info.get('card') or {}
        if not card.get('doc'):
            return None
        html = self._gr_cardDoc(card['doc'], abs_path=abs_path, table=table, pkg=pkg)
        return dict(title=self._(card.get('title') or info.get('caption') or resource),
                    html=self._(html), doc_kw=card.get('doc_kw') or {}, tags=card.get('doc_tags'))

    def doc_help(self, target, helpcode, language=None):
        table, _, resource_class = target.partition('/')
        if table.count('.') != 1:
            return None
        names = [f"th_{table.split('.')[1]}_{resource_class}"] if resource_class else []
        for name in names + [None]:
            data, _ = self.getHelperData(table=table, name=name)
            node = data.getNode(helpcode)
            text = node.attr.get(language) if node else None
            if text:
                paragraphs = re.split(r'\n\s*\n', escape(text.strip()))
                html = ''.join(f"<p>{p.replace(chr(10), '<br>')}</p>" for p in paragraphs)
                return dict(title=helpcode, html=html)
        return None

    def doc_docu(self, target, hierarchical_name, language=None):
        if 'docu' not in self.db.packages:
            return None
        doc = self.db.table(target or 'docu.documentation').documentRst(hierarchical_name,
                                                                         language=language)
        if not doc:
            return None
        return dict(title=doc['title'], page=self.site.getService('rst2html')(doc['rst']))
