"""The calls the login page declares, recorded and redirected when the page is built.

The struct nodes are what the login dialog and the ``rootenvForm_<pkg>``
hooks add: a dbSelect is redirected to ``login_fieldSelect`` and records its
table, structure and condition parameters; ``validate_nodup`` /
``validate_exist`` become a ``validate_remote`` on ``login_fieldCount``; a public
callable in any attribute records its module and qualified name.
"""
from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method
from gnr.web.loginfields import (collect_login_rpcs, without_field_rpcs, dbselect_kwargs,
                                 declared_method, callable_key)


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
    box.setItem('username', None, tag='textbox', value='^.username',
                validate_nodup='adm.user.username', validate_nodup_error='Taken')
    box.setItem('email', None, tag='textbox', value='^.email', validate_exist=True, dbfield='adm.user.email')
    box.setItem('relative', None, tag='textbox', value='^.x', validate_nodup='adm.user.code',
                validate_nodup_relative='group_code')
    box.setItem('remote', None, tag='dataRemote', method='_table.dmt.sede.lookup')
    form.setItem('box', box, tag='div')
    return form


def test_the_struct_is_recorded_and_redirected():
    form = _fields()
    recorded = collect_login_rpcs(form.nodes)
    assert recorded['methods'] == [callable_key(COMPONENT.login_sedi), 'login_checkCode',
                                   '_table.dmt.sede.lookup']
    assert recorded['counts'] == ['adm.user.username', 'adm.user.email']
    consultorio, sede = recorded['dbselects']
    assert consultorio == dict(dbtable='dmt.consultorio',
                               structure=dict(condition='$abilitato IS TRUE AND $op=:env_op',
                                              hiddenColumns='codice'),
                               dynamic=[], params=['env_op'], pinned=dict(env_op='operatore_id'))
    assert (sede['params'], sede['pinned']) == (['c'], {})
    assert form.getAttr('consultorio')['method'] == 'login_fieldSelect'
    assert form.getAttr('sede')['method'] == 'login_fieldSelect'
    username = form.getAttr('box.username')
    assert 'validate_nodup' not in username
    assert (username['validate_remote'], username['validate_login_field'], username['validate_login_check'],
            username['validate_remote_error']) == ('login_fieldCount', 'adm.user.username', 'nodup', 'Taken')
    assert form.getAttr('box.email')['validate_login_check'] == 'exist'
    assert form.getAttr('box.relative')['validate_nodup'] == 'adm.user.code'


def test_a_second_pass_records_nothing_new():
    form = _fields()
    first = collect_login_rpcs(form.nodes)
    again = without_field_rpcs(collect_login_rpcs(form.nodes), first)
    assert (again['methods'], again['dbselects'], again['counts']) == ([], [], [])


def test_dbselect_runs_with_the_declared_structure_and_client_values_only():
    sent = dict(dbtable='dmt.sede', condition='1=1', auxColumns='$secret', hiddenColumns='$pwd',
                ignorePartition=True, subtable='*', _storename='other', selectmethod='app.getSelection',
                c='C1', _id='S1', limit=0, unexpected='x')
    assert dbselect_kwargs(collect_login_rpcs(_fields().nodes), sent) == dict(
        dbtable='dmt.sede', auxColumns='$indirizzo', condition='$consultorio_id=:c', c='C1', _id='S1', limit=0)


def test_dbselect_on_an_undeclared_table_is_refused():
    assert dbselect_kwargs(collect_login_rpcs(_fields().nodes), dict(dbtable='adm.user')) is None


def test_a_dynamic_structure_attribute_keeps_the_client_value():
    form = Bag()
    form.setItem('f', None, tag='dbSelect', dbtable='dmt.sede', condition='^.cond')
    assert dbselect_kwargs(collect_login_rpcs(form.nodes), dict(dbtable='dmt.sede', condition='$x=1')) \
        == dict(dbtable='dmt.sede', condition='$x=1')


def test_declared_methods_are_served_by_name_or_callable():
    recorded = collect_login_rpcs(_fields().nodes)
    assert declared_method(COMPONENT.login_sedi, '*|login:LoginComponent;login_sedi', recorded)
    assert declared_method(object(), '_table.dmt.sede.lookup', recorded)
    assert not declared_method(COMPONENT.plain, 'plain', recorded)
    assert not declared_method(COMPONENT.login_sedi, 'login_sedi', None)


def test_rootenv_parameters_come_from_the_checked_rootenv():
    recorded = collect_login_rpcs(_fields().nodes)
    rootenv = Bag(dict(operatore_id='OP1', consultorio_id='C9'))
    sent = dict(dbtable='dmt.consultorio', env_op='OTHER', _querystring='*')
    assert dbselect_kwargs(recorded, sent, rootenv)['env_op'] == 'OP1'
    assert dbselect_kwargs(recorded, sent)['env_op'] == 'OTHER'


def test_a_value_chosen_in_the_form_stays_the_client_one():
    recorded = collect_login_rpcs(_fields().nodes)
    rootenv = Bag(dict(consultorio_id='C9'))
    assert dbselect_kwargs(recorded, dict(dbtable='dmt.sede', c='C1'), rootenv)['c'] == 'C1'


def test_an_absolute_rootenv_path_is_pinned_too():
    form = Bag()
    form.setItem('f', None, tag='dbSelect', dbtable='erp.ufficio', condition='$staff_id=:staff_id',
                 condition_staff_id='=gnr.rootenv.staff_id')
    recorded = collect_login_rpcs(form.nodes)
    assert dbselect_kwargs(recorded, dict(dbtable='erp.ufficio', staff_id='X'), Bag(dict(staff_id='S1'))) \
        == dict(dbtable='erp.ufficio', condition='$staff_id=:staff_id', staff_id='S1')
