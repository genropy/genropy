#!/usr/bin/env python
# encoding: utf-8
from urllib.parse import urljoin, urlsplit

from gnr.app.gnrdbo import GnrDboTable, GnrDboPackage

class Package(GnrDboPackage):
    def config_attributes(self):
        return dict(comment='docu package',sqlschema='docu',sqlprefix=True,
                    name_short='Docu', name_long='Documentation', name_full='Docu')
                    
    def htmlProcessorName(self):
        return '/docu/index/rst'

    def config_db(self, pkg):
        pass
        
        
class Table(GnrDboTable):
    
    def _absoluteLocation(self, location):
        """Give scheme and host to a host-relative documentation url.

        The documentation may be served by a different host than the instance, so
        a redirect Location and a link out of the instance must carry the docs host
        explicitly. handbook_url is normally absolute (the sphinx export builds it
        from the docu.sphinx_baseurl preference), but a relative one is resolved
        here against that same preference."""
        if urlsplit(location).netloc:
            return location
        base_url = self.db.application.getPreference('.sphinx_baseurl', pkg='docu') or ''
        if not urlsplit(base_url).netloc:
            return location
        return urljoin(base_url, location)

    def _distinctAncestors(self, rows):
        """Collapse the ancestors rows of calculateExternalUrl to one row per document.

        ``@handbooks`` is a one-to-many relation: nothing forbids two handbooks
        from sharing a docroot (a published one and a local zipped one, or a
        leftover duplicate), and the join then repeats that ancestor once per
        handbook. The repeated row is not recognized as the handbook root and
        ends up among the path segments, doubling the handbook root name in the
        url. Local handbooks are downloadable zips with no published site, so
        they never name a url and their rows count as plain path segments."""
        merged = {}
        for row in rows:
            row = dict(row)
            if row.get('handbook_is_local'):
                row['handbook_url'] = None
                row['handbook_toc_roots'] = None
            pkey = row.get('id') or row.get('pkey')
            previous = merged.get(pkey)
            if previous is None or (row.get('handbook_url') and not previous.get('handbook_url')):
                merged[pkey] = row
        return list(merged.values())

    def calculateExternalUrl(self, doc_record):
        pkey = doc_record.get('id') or doc_record.get('pkey')
        if not pkey:
            return
        ancestors = self.db.table('docu.documentation').hierarchicalHandler.getAncestors(
                        pkey=pkey, meToo=True,
                        columns='$id,$name,$child_count,@handbooks.handbook_url AS handbook_url,@handbooks.toc_roots AS handbook_toc_roots,@handbooks.is_local_handbook AS handbook_is_local',
                        order_by='$hlevel')
        if not ancestors:
            return
        rows = ancestors.output('dictlist') if hasattr(ancestors, 'output') else ancestors
        rows = self._distinctAncestors(rows)
        base_url = doc_record.get('root_handbook_url')
        segments = []
        collecting = False
        root_doc_id = None
        toc_roots_set = set()
        for ancestor in rows:
            handbook_url = ancestor.get('handbook_url')
            if handbook_url and not collecting:
                base_url = handbook_url
                collecting = True
                root_doc_id = ancestor.get('id')
                toc_roots_str = ancestor.get('handbook_toc_roots') or ''
                toc_roots_set = {token for token in toc_roots_str.split(',') if token}
                continue
            if not collecting:
                continue
            name = ancestor.get('name')
            if name:
                segments.append(name)
        if not base_url:
            return
        base = base_url.rstrip('/')
        doc_record_id = doc_record.get('id') or doc_record.get('pkey')
        doc_record_name = doc_record.get('name')
        child_count = doc_record.get('child_count') or 0
        has_children = child_count > 0
        is_root_doc = doc_record_id == root_doc_id
        is_toc_root = doc_record_id in toc_roots_set if doc_record_id else False
        if is_root_doc:
            return f"{base}/index.html"
        if is_toc_root:
            folder_parts = segments or ([doc_record_name] if doc_record_name else [])
            folder = f"{base}/{'/'.join(folder_parts)}" if folder_parts else base
            return f"{folder}/index.html"
        if not segments:
            if not doc_record_name:
                return base
            if has_children:
                return f"{base}/{doc_record_name}/{doc_record_name}.html"
            else:
                return f"{base}/{doc_record_name}.html"
        doc_record_segment = segments[-1]
        ancestor_dirs = segments[:-1]
        if has_children:
            dirs = segments
            filename = doc_record_name or doc_record_segment
        else:
            dirs = ancestor_dirs
            filename = doc_record_name or doc_record_segment
        path_parts = dirs + [f"{filename}.html"]
        return f"{base}/{'/'.join(path_parts)}"
