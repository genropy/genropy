"""The calls of the login dialog fields, recorded at build time and served before doLogin.

The fields are struct nodes as ``rootenvForm_<pkg>`` hooks add them: a dbSelect
records its table, structure and condition parameters, a public callable in
any attribute (dataRpc method, validate_remote) records its qualified name.
"""
from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method
from gnr.web.loginfields import collect_field_rpcs, field_rpc_call


class LoginComponent(object):
    @public_method
    def login_sedi(self, consultorio_id=None):
        return consultorio_id

    def plain(self):
        pass


COMPONENT = LoginComponent()


def _fields():
    form = Bag()
    form.setItem('consultorio', None, tag='dbSelect', value='^.consultorio_id',
                 table='dmt.consultorio', condition='$abilitato IS TRUE AND $op=:env_op',
                 condition_env_op='=.operatore_id', hasDownArrow=True,
                 selected_codice='.codice')
    form.setItem('sede', None, tag='DbSelect', value='^.sede_id', dbtable='dmt.sede',
                 condition='$consultorio_id=:c', condition_c='^.consultorio_id',
                 auxColumns='$indirizzo')
    form.setItem('rpc', None, tag='dataRpc', path='_login.sedi', method=COMPONENT.login_sedi,
                 consultorio_id='^.consultorio_id')
    box = Bag()
    box.setItem('code', None, tag='textbox', value='^.code', validate_remote='login_checkCode',
                validate_onAccept=COMPONENT.plain)
    box.setItem('remote', None, tag='dataRemote', method='_table.dmt.sede.lookup')
    form.setItem('box', box, tag='div')
    return form


def test_fields_record_dbselects_and_public_callables():
    recorded = collect_field_rpcs(_fields().nodes)
    assert recorded['methods'] == ['LoginComponent.login_sedi', 'login_checkCode', '_table.dmt.sede.lookup']
    consultorio, sede = recorded['dbselects']
    assert consultorio == dict(dbtable='dmt.consultorio',
                               structure=dict(condition='$abilitato IS TRUE AND $op=:env_op',
                                              hiddenColumns='codice'),
                               dynamic=[], params=['env_op'])
    assert sede == dict(dbtable='dmt.sede',
                        structure=dict(auxColumns='$indirizzo', condition='$consultorio_id=:c'),
                        dynamic=[], params=['c'])


class _App(object):
    def __init__(self):
        self.calls = []

    @public_method
    def dbSelect(self, **kwargs):
        self.calls.append(kwargs)


def _recorded():
    return collect_field_rpcs(_fields().nodes)


def test_dbselect_runs_with_the_declared_structure_and_client_values_only():
    app = _App()
    sent = dict(dbtable='dmt.sede', condition='1=1', auxColumns='$secret', hiddenColumns='$pwd',
                ignorePartition=True, subtable='*', _storename='other', selectmethod='app.getSelection',
                c='C1', _id='S1', limit=0, unexpected='x')
    call = field_rpc_call(app.dbSelect, 'app.dbSelect', sent, _recorded())
    call(**sent)
    assert app.calls == [dict(dbtable='dmt.sede', auxColumns='$indirizzo', condition='$consultorio_id=:c',
                              c='C1', _id='S1', limit=0)]


def test_dbselect_on_an_undeclared_table_is_refused():
    app = _App()
    assert field_rpc_call(app.dbSelect, 'app.dbSelect', dict(dbtable='adm.user'), _recorded()) is None


def test_a_dynamic_structure_attribute_keeps_the_client_value():
    form = Bag()
    form.setItem('f', None, tag='dbSelect', dbtable='dmt.sede', condition='^.cond')
    app = _App()
    call = field_rpc_call(app.dbSelect, 'app.dbSelect', dict(dbtable='dmt.sede', condition='$x=1'),
                          collect_field_rpcs(form.nodes))
    call()
    assert app.calls == [dict(dbtable='dmt.sede', condition='$x=1')]


def test_declared_methods_are_served_by_name_or_qualified_name():
    recorded = _recorded()
    assert field_rpc_call(COMPONENT.login_sedi, '*|login:LoginComponent;login_sedi', {}, recorded) \
        == COMPONENT.login_sedi
    lookup = object()
    assert field_rpc_call(lookup, '_table.dmt.sede.lookup', {}, recorded) is lookup


def test_undeclared_methods_are_refused():
    recorded = _recorded()
    assert field_rpc_call(COMPONENT.plain, 'plain', {}, recorded) is None
    assert field_rpc_call(COMPONENT.login_sedi, 'login_sedi', {}, None) is None
