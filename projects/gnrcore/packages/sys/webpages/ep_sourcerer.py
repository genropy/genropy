# -*- coding: utf-8 -*-

from gnr.core.gnrdecorator import public_method
from gnr.core.gnrbag import Bag
from gnr.web.verifiers import AuthorizationBearerVerifier


MAX_ROWS = 1000


def _classify_column(attr):
    if attr.get('joiner') or attr.get('tag') == 'relation':
        return 'relation', False
    if not attr.get('virtual_column'):
        return 'real', False
    if attr.get('relation_path'):
        return 'alias', False
    if attr.get('select'):
        return 'formula_subquery', True
    if attr.get('bagcolumn') or attr.get('itempath'):
        return 'bagitem', False
    if attr.get('sql_formula'):
        return 'formula_sql', False
    if attr.get('py_method') or attr.get('pyColumn'):
        return 'pycolumn', False
    return 'virtual_other', False


def _attr_to_json(attr):
    out = {}
    for k, v in attr.items():
        if isinstance(v, (str, int, float, bool, type(None))):
            out[k] = v
        elif isinstance(v, dict):
            sub = {sk: sv for sk, sv in v.items()
                   if isinstance(sv, (str, int, float, bool, type(None)))}
            if sub:
                out[k] = sub
    return out


def _bag_to_json(bag, depth=1):
    if bag is None:
        return None
    out = {}
    for node in bag:
        attr = node.attr
        kind, has_subquery = _classify_column(attr)
        item = {'attr': _attr_to_json(attr), 'kind': kind}
        if has_subquery:
            item['subquery'] = True
        v = node.value
        if v is None:
            pass
        elif hasattr(v, 'load') and not hasattr(v, 'nodes'):
            item['lazy'] = True
        elif hasattr(v, 'nodes'):
            if depth > 0:
                item['children'] = _bag_to_json(v, depth=depth - 1)
            else:
                item['truncated'] = True
        out[node.label] = item
    return out


def _build_table_schema(db, table_fullname):
    tbl_model = db.model.table(table_fullname)
    tree_bag = tbl_model.newRelationResolver().load()
    schema = _bag_to_json(tree_bag) or {}
    vcols = tbl_model.get('virtual_columns')
    if vcols:
        for name, vc in vcols.items():
            attr = dict(vc.attributes)
            kind, has_subquery = _classify_column(attr)
            entry = {'attr': _attr_to_json(attr), 'kind': kind}
            if has_subquery:
                entry['subquery'] = True
            schema[name] = entry
    return schema


class SourcererBearerVerifier(AuthorizationBearerVerifier):
    def get_token_to_verify(self):
        service = self.page.getService('sourcerer')
        if service:
            return service.token


class GnrCustomWebPage(object):
    py_requires = 'gnrcomponents/externalcall:BaseRpc'

    @public_method(verifier=SourcererBearerVerifier)
    def rpc_health(self, **kwargs):
        return Bag(dict(result='ok'))

    @public_method(verifier=SourcererBearerVerifier)
    def rpc_query(self, ticket_code=None, **kwargs):
        info = {'endpoint': 'rpc_query', 'error': None}

        service = self.getService('sourcerer')
        if not service or not service.is_query_enabled():
            info['error'] = 'endpoint_disabled'
            return {'ok': False, 'ticket_code': ticket_code,
                    'info': info, 'data': []}

        count_only = bool(kwargs.get('countOnly'))
        if count_only:
            cap_applied = False
            info['limit_applied'] = kwargs.get('limit')
        else:
            requested = kwargs.get('limit')
            cap_applied = requested is None or (
                isinstance(requested, int) and requested > MAX_ROWS)
            kwargs['limit'] = MAX_ROWS if cap_applied else requested
            info['limit_applied'] = kwargs['limit']

        kwargs.pop('recordResolver', None)

        try:
            adapter_name = type(self.db.adapter).__name__.lower()
            if 'postgres' in adapter_name or 'pg' in adapter_name:
                self.db.execute("SET LOCAL statement_timeout = 3000")
        except Exception:
            pass

        try:
            data_bag, attrs = self.app.getSelection(
                recordResolver=False, **kwargs)
            rows = []
            if not count_only:
                for k in data_bag.keys():
                    node = data_bag.getNode(k)
                    row = dict(node.attr)
                    row.pop('_customClasses', None)
                    row.pop('_attributes', None)
                    rows.append(row)
            info['totalrows'] = attrs.get('totalrows', 0)
            info['more'] = cap_applied and info['totalrows'] >= MAX_ROWS
            info['servertime_ms'] = attrs.get('servertime')
            return {'ok': True, 'ticket_code': ticket_code,
                    'info': info, 'data': rows}
        except Exception as e:
            info['error'] = str(e)
            return {'ok': False, 'ticket_code': ticket_code,
                    'info': info, 'data': []}

    @public_method(verifier=SourcererBearerVerifier)
    def rpc_relationtree(self, ticket_code=None, table=None, **kwargs):
        info = {'endpoint': 'rpc_relationtree', 'error': None}

        service = self.getService('sourcerer')
        if not service or not service.is_query_enabled():
            info['error'] = 'endpoint_disabled'
            return {'ok': False, 'ticket_code': ticket_code,
                    'info': info, 'tables': None, 'trees': None}

        if not table:
            try:
                tables = sorted(t.fullname for t in self.db.tables)
                return {'ok': True, 'ticket_code': ticket_code,
                        'info': info, 'tables': tables, 'trees': None}
            except Exception as e:
                info['error'] = str(e)
                return {'ok': False, 'ticket_code': ticket_code,
                        'info': info, 'tables': None, 'trees': None}

        requested = [t.strip() for t in str(table).split(',') if t.strip()]
        info['tables_requested'] = requested
        trees = {}
        failed = {}
        for tname in requested:
            try:
                trees[tname] = _build_table_schema(self.db, tname)
            except Exception as e:
                failed[tname] = str(e)
        if failed:
            info['tables_failed'] = failed

        if not trees:
            info['error'] = 'no_table_resolved'
            return {'ok': False, 'ticket_code': ticket_code,
                    'info': info, 'tables': None, 'trees': None}

        return {'ok': True, 'ticket_code': ticket_code,
                'info': info, 'tables': None, 'trees': trees}
