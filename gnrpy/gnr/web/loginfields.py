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
``login_fieldSelect`` with an id of its own and runs with the table, columns and
condition its field declared, taking from the client only the search text, the
key and the condition values chosen in the form (those read from the rootenv
come from the rootenv the server built at the avatar check); a field whose
structure is bound to client data is not served, and a key outside the
condition gives no row; ``validate_nodup`` / ``validate_exist`` become a
``validate_remote`` on ``login_fieldCount``, which counts only on the declared
field. Public callables the struct references (dataRpc, validate_remote) are
served by the exact name the client gets for them. Subtrees the user may not
see (``__forbidden__``) are skipped, as the serializer does.
"""
from gnr.core.gnrbag import Bag
from gnr.core.gnrlang import serializedFuncName

DBSELECT_TAGS = ('dbselect', 'dbcombobox')
DBSELECT_METHOD = 'app.dbSelect'
FIELD_SELECT_METHOD = 'login_fieldSelect'
FIELD_COUNT_METHOD = 'login_fieldCount'
FIELD_ID_PARAM = 'login_field'
GENERIC_PREFIXES = ('app.',)
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
    for key in DBSELECT_STRUCTURE:
        if key not in attr:
            continue
        if _is_dynamic(attr[key]):
            return
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
    return dict(dbtable=dbtable, structure=structure, params=params, pinned=pinned)


def rpc_name(value):
    """The method name the client gets for a public callable, as the struct serializes it."""
    try:
        return serializedFuncName(value)
    except AttributeError:
        return None


def _servable(name):
    return bool(name) and not name.startswith(GENERIC_PREFIXES) \
        and name not in (DBSELECT_METHOD, FIELD_SELECT_METHOD, FIELD_COUNT_METHOD)


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


def form_value_keys(nodes):
    """The rootenv keys the fields among ``nodes`` edit (``value='^.x'``), skipping forbidden subtrees."""
    keys = []

    def walk(node_list):
        for node in node_list:
            if node.attr.get('__forbidden__'):
                continue
            key = _rootenv_key(node.attr.get('value'))
            if key and key not in keys:
                keys.append(key)
            value = node.getValue()
            if isinstance(value, Bag):
                walk(value.nodes)

    walk(nodes)
    return keys


def trusted_rootenv(page_rootenv, checked_rootenv, sent_rootenv, field_keys):
    """The rootenv a login stores: the page's and the one the server built at the avatar check,
    with from the client only the values of the login form fields."""
    rootenv = Bag(page_rootenv or {})
    rootenv.update(Bag(checked_rootenv or {}))
    sent_rootenv = sent_rootenv or Bag()
    for key in field_keys or []:
        if key in sent_rootenv:
            rootenv[key] = sent_rootenv[key]
    return rootenv


def collect_login_rpcs(nodes, field_prefix='f'):
    """Record the calls the struct ``nodes`` declare and redirect dbSelect and duplicate checks.

    ``field_prefix`` keeps the dbSelect ids of two recordings apart. Returns a Bag
    ready for the page store."""
    methods = []
    dbselects = []
    counts = []
    form_values = set(form_value_keys(nodes))

    def walk(node_list):
        for node in node_list:
            attr = node.attr
            if attr.get('__forbidden__'):
                continue
            tag = (attr.get('tag') or '').lower()
            if tag in DBSELECT_TAGS and attr.get('method', DBSELECT_METHOD) == DBSELECT_METHOD:
                spec = _dbselect_spec(attr, form_values)
                if spec:
                    spec['id'] = '%s%i' % (field_prefix, len(dbselects))
                    dbselects.append(spec)
                    attr['method'] = FIELD_SELECT_METHOD
                    attr['condition_%s' % FIELD_ID_PARAM] = spec['id']
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
                    name = rpc_name(value)
                elif key in RPC_KEYS and isinstance(value, str):
                    name = value
                else:
                    continue
                if _servable(name):
                    methods.append(name)
            value = node.getValue()
            if isinstance(value, Bag):
                walk(value.nodes)

    walk(nodes)
    return Bag(dict(methods=methods, dbselects=dbselects, counts=counts))


def without_field_rpcs(page_rpcs, field_rpcs):
    """``page_rpcs`` less the calls of ``field_rpcs``, which wait for the avatar check."""
    if not field_rpcs:
        return page_rpcs
    return Bag(dict((key, [item for item in page_rpcs[key] or [] if item not in (field_rpcs[key] or [])])
                    for key in RECORDED_KEYS))


def dbselect_kwargs(recorded, kwargs, rootenv=None):
    """The kwargs of the recorded dbSelect field ``kwargs['login_field']`` on ``kwargs['dbtable']``, or None.

    A condition parameter that reads the rootenv (not a value chosen in the form)
    takes its value from ``rootenv``, the one the server built at the avatar check."""
    spec = next((s for s in recorded['dbselects'] or []
                 if s['id'] == kwargs.get(FIELD_ID_PARAM) and s['dbtable'] == kwargs.get('dbtable')), None)
    if not spec:
        return
    served = dict(spec['structure'])
    for key in DBSELECT_CLIENT_KEYS + tuple(spec['params']):
        if key in kwargs:
            served[key] = kwargs[key]
    for param, key in (spec.get('pinned') or {}).items():
        if rootenv is not None and rootenv[key] is not None:
            served[param] = rootenv[key]
    served['dbtable'] = spec['dbtable']
    return served


def declared_method(method, recorded):
    """True when a recorded struct declares exactly ``method``."""
    return bool(recorded) and _servable(method) and method in (recorded['methods'] or [])
