"""The calls the login page declares, served to a request without a session.

A protected page shows the login dialog to a visitor without a session, and
everything that dialog contains calls the server before anybody is logged:
the login buttons of extension packages, the new user and password forms,
the fields ``rootenvForm_<pkg>`` hooks add. When the page is built its struct
is walked: the calls are recorded in the page store and served only as
recorded:

- the calls of the login page, to anybody (``login_page_rpcs``);
- the calls of the ``rootenvForm`` fields, once ``login_checkAvatar`` has
  checked the avatar (``login_field_rpcs``).

Generic app rpcs are never opened. A dbSelect is redirected to the page's
``login_fieldSelect`` and runs with the table, columns and condition its field
declared, taking from the client only the search text, the key and the
condition values chosen in the form (those read from the rootenv come from
the rootenv the server built at the avatar check); ``validate_nodup`` / ``validate_exist`` become a
``validate_remote`` on ``login_fieldCount``, which counts only on the declared
field. Public callables the struct references (dataRpc, validate_remote) are
served by name.
"""
from gnr.core.gnrbag import Bag

DBSELECT_TAGS = ('dbselect', 'dbcombobox')
DBSELECT_METHOD = 'app.dbSelect'
FIELD_SELECT_METHOD = 'login_fieldSelect'
FIELD_COUNT_METHOD = 'login_fieldCount'
RPC_KEYS = ('method', 'validate_remote')
COUNT_CHECKS = ('nodup', 'exist')
DBSELECT_STRUCTURE = ('columns', 'auxColumns', 'hiddenColumns', 'alternatePkey', 'rowcaption',
                      'order_by', 'preferred', 'invalidItemCondition', 'subtable', 'condition',
                      'selectmethod', 'applymethod', 'weakCondition', 'excludeDraft',
                      'ignorePartition', 'distinct', 'emptyLabel', 'emptyLabel_first',
                      'emptyLabel_class', '_storename')
DBSELECT_CLIENT_KEYS = ('_id', '_querystring', 'querystring', 'limit', 'exclude',
                        'ignoreCase', 'notnull')
RECORDED_KEYS = ('methods', 'dbselects', 'counts')


def _is_dynamic(value):
    return isinstance(value, str) and value[:1] in ('^', '=')


def _rootenv_key(value):
    """The rootenv key a ``^.x`` / ``=.x`` / ``=gnr.rootenv.x`` path reads, or None."""
    if not _is_dynamic(value):
        return
    path = value[1:]
    if path.startswith('.'):
        key = path[1:]
    elif path.startswith('gnr.rootenv.'):
        key = path[len('gnr.rootenv.'):]
    else:
        return
    if key and not any(c in key for c in '.?#'):
        return key


def _dbselect_spec(attr, form_values=()):
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
    pinned = {}
    for param in params:
        key = _rootenv_key(attr['condition_%s' % param])
        if key and key not in form_values:
            pinned[param] = key
    return dict(dbtable=dbtable, structure=structure, dynamic=dynamic, params=params, pinned=pinned)


def callable_key(value):
    func = getattr(value, '__func__', value)
    qualname = getattr(func, '__qualname__', None)
    if qualname:
        return '%s:%s' % (getattr(func, '__module__', ''), qualname)


def _count_check(attr):
    """(check, field) of a validate_nodup / validate_exist the login page can serve, or None."""
    for check in COUNT_CHECKS:
        key = 'validate_%s' % check
        if key not in attr or 'validate_remote' in attr:
            continue
        if any(k.startswith('%s_' % key) and k != '%s_error' % key for k in attr):
            return
        field = attr[key]
        if field is True:
            field = attr.get('dbfield')
        if isinstance(field, str) and field.count('.') == 2 and not _is_dynamic(field):
            return check, field


def collect_login_rpcs(nodes):
    """Record the calls the struct ``nodes`` declare and redirect dbSelect and duplicate checks.

    Returns a Bag ready for the page store."""
    methods = []
    dbselects = []
    counts = []
    form_values = set()

    def values(node_list):
        for node in node_list:
            key = _rootenv_key(node.attr.get('value'))
            if key:
                form_values.add(key)
            value = node.getValue()
            if isinstance(value, Bag):
                values(value.nodes)

    def walk(node_list):
        for node in node_list:
            attr = node.attr
            tag = (attr.get('tag') or '').lower()
            if tag in DBSELECT_TAGS and attr.get('method', DBSELECT_METHOD) == DBSELECT_METHOD:
                spec = _dbselect_spec(attr, form_values)
                if spec:
                    dbselects.append(spec)
                    attr['method'] = FIELD_SELECT_METHOD
            count = _count_check(attr)
            if count:
                check, field = count
                counts.append(field)
                attr.pop('validate_%s' % check)
                error = attr.pop('validate_%s_error' % check, None)
                attr['validate_remote'] = FIELD_COUNT_METHOD
                attr['validate_login_field'] = field
                attr['validate_login_check'] = check
                if error:
                    attr['validate_remote_error'] = error
            for key, value in list(attr.items()):
                if callable(value) and getattr(value, 'is_rpc', False):
                    methods.append(callable_key(value))
                elif key in RPC_KEYS and isinstance(value, str) \
                        and value not in (DBSELECT_METHOD, FIELD_SELECT_METHOD, FIELD_COUNT_METHOD):
                    methods.append(value)
            value = node.getValue()
            if isinstance(value, Bag):
                walk(value.nodes)

    values(nodes)
    walk(nodes)
    return Bag(dict(methods=methods, dbselects=dbselects, counts=counts))


def without_field_rpcs(page_rpcs, field_rpcs):
    """``page_rpcs`` less the calls of ``field_rpcs``, which wait for the avatar check."""
    if not field_rpcs:
        return page_rpcs
    return Bag(dict((key, [item for item in page_rpcs[key] or [] if item not in (field_rpcs[key] or [])])
                    for key in RECORDED_KEYS))


def dbselect_kwargs(recorded, kwargs, rootenv=None):
    """The kwargs of the dbSelect a recorded field declared for ``kwargs['dbtable']``, or None.

    A condition parameter that reads the rootenv (not a value chosen in the form)
    takes its value from ``rootenv``, the one the server built at the avatar check."""
    specs = [s for s in recorded['dbselects'] or [] if s['dbtable'] == kwargs.get('dbtable')]
    if not specs:
        return
    sent = set(kwargs)
    spec = next((s for s in specs if set(s['params']) <= sent), specs[0])
    served = dict(spec['structure'])
    for key in DBSELECT_CLIENT_KEYS + tuple(spec['params']) + tuple(spec['dynamic']):
        if key in kwargs:
            served[key] = kwargs[key]
    for param, key in (spec.get('pinned') or {}).items():
        if rootenv is not None and rootenv[key] is not None:
            served[param] = rootenv[key]
    served['dbtable'] = spec['dbtable']
    return served


def declared_method(handler, method, recorded):
    """True when a recorded struct references ``handler`` or names ``method``."""
    if not handler or not recorded:
        return False
    methods = recorded['methods'] or []
    return method in methods or callable_key(handler) in methods
