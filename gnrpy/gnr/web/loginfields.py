"""The rpcs the login dialog fields declare, served before doLogin.

Between ``login_checkAvatar`` and ``doLogin`` the page has no logged user, yet
the fields that ``rootenvForm_<pkg>`` hooks add to the dialog call the server:
dbSelect lookups, dataRpc, validate_remote. When the dialog is built their
calls are recorded in the page store; in that window only those are served,
and a dbSelect runs with the table, columns and condition the field declared,
taking from the client only the search text, the key and the condition values.
"""
from gnr.core.gnrbag import Bag

DBSELECT_TAGS = ('dbselect', 'dbcombobox')
RPC_KEYS = ('method', 'validate_remote')
DBSELECT_METHOD = 'app.dbSelect'
DBSELECT_STRUCTURE = ('columns', 'auxColumns', 'hiddenColumns', 'alternatePkey', 'rowcaption',
                      'order_by', 'preferred', 'invalidItemCondition', 'subtable', 'condition',
                      'selectmethod', 'applymethod', 'weakCondition', 'excludeDraft',
                      'ignorePartition', 'distinct', 'emptyLabel', 'emptyLabel_first',
                      'emptyLabel_class', '_storename')
DBSELECT_CLIENT_KEYS = ('_id', '_querystring', 'querystring', 'limit', 'exclude',
                        'ignoreCase', 'notnull')


def _is_dynamic(value):
    return isinstance(value, str) and value[:1] in ('^', '=')


def _dbselect_spec(attr):
    dbtable = attr.get('dbtable') or attr.get('table')
    if not dbtable or _is_dynamic(dbtable):
        return
    structure = {}
    dynamic = []
    for key in DBSELECT_STRUCTURE:
        if key not in attr:
            continue
        if _is_dynamic(attr[key]):
            dynamic.append(key)
        else:
            structure[key] = attr[key]
    selected = [value.split('=')[1] if '=' in value else key[len('selected_'):]
                for key, value in attr.items() if key.startswith('selected_') and value]
    if selected:
        hidden = [c for c in (structure.get('hiddenColumns') or '').split(',') if c]
        structure['hiddenColumns'] = ','.join(hidden + [c for c in selected if c not in hidden])
    params = [key[len('condition_'):] for key in attr if key.startswith('condition_')]
    return dict(dbtable=dbtable, structure=structure, dynamic=dynamic, params=params)


def _callable_name(value):
    if callable(value) and getattr(value, 'is_rpc', False):
        return getattr(value, '__qualname__', None)


def collect_field_rpcs(nodes):
    """The rpcs the struct ``nodes`` declare, as a Bag ready for the page store."""
    methods = []
    dbselects = []

    def walk(node_list):
        for node in node_list:
            attr = node.attr
            tag = (attr.get('tag') or '').lower()
            if tag in DBSELECT_TAGS and attr.get('method', DBSELECT_METHOD) == DBSELECT_METHOD:
                spec = _dbselect_spec(attr)
                if spec:
                    dbselects.append(spec)
            for key, value in attr.items():
                name = _callable_name(value)
                if name:
                    methods.append(name)
                elif key in RPC_KEYS and isinstance(value, str) and value != DBSELECT_METHOD:
                    methods.append(value)
            value = node.getValue()
            if isinstance(value, Bag):
                walk(value.nodes)

    walk(nodes)
    return Bag(dict(methods=methods, dbselects=dbselects))


def _dbselect_kwargs(spec, kwargs):
    served = dict(spec['structure'])
    for key in DBSELECT_CLIENT_KEYS + tuple(spec['params']) + tuple(spec['dynamic']):
        if key in kwargs:
            served[key] = kwargs[key]
    served['dbtable'] = spec['dbtable']
    return served


def field_rpc_call(handler, method, kwargs, recorded):
    """``handler`` bound to what a recorded login field may send, or None when no field declares this call."""
    if not handler or not recorded:
        return
    if method == DBSELECT_METHOD:
        specs = [s for s in recorded['dbselects'] or [] if s['dbtable'] == (kwargs or {}).get('dbtable')]
        if not specs:
            return
        sent = set(kwargs)
        spec = next((s for s in specs if set(s['params']) <= sent), specs[0])
        served = _dbselect_kwargs(spec, kwargs)
        return lambda **ignored: handler(**served)
    methods = recorded['methods'] or []
    if method in methods or getattr(handler, '__qualname__', None) in methods:
        return handler
