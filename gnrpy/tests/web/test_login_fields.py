"""The calls the login page declares, recorded and redirected when the page is built.

The struct nodes are what the login dialog and the ``rootenvForm_<pkg>``
hooks add: a dbSelect is redirected to ``login_fieldSelect`` with an id of its
own and records its table, structure and condition parameters;
``validate_nodup`` / ``validate_exist`` become a ``validate_remote`` on
``login_fieldCount``; a public callable records the exact name the client gets.
"""
from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method
from gnr.web.loginfields import (collect_login_rpcs, without_field_rpcs, dbselect_kwargs,
                                 declared_method, rpc_name, form_value_keys, trusted_rootenv)


class LoginComponent(object):
    @public_method
    def login_sedi(self, consultorio_id=None):
        return consultorio_id

    @public_method
    def admin_only(self):
        pass

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
    form.setItem('sede_bis', None, tag='dbSelect', value='^.sede_bis_id', dbtable='dmt.sede',
                 condition='$consultorio_id=:c AND $principale IS TRUE', condition_c='^.consultorio_id')
    form.setItem('rpc', None, tag='dataRpc', path='_login.sedi', method=COMPONENT.login_sedi,
                 consultorio_id='^.consultorio_id')
    form.setItem('generic', None, tag='dataRpc', path='_login.all', method='app.getSelection')
    box = Bag()
    box.setItem('code', None, tag='textbox', value='^.code', validate_remote='login_checkCode',
                validate_onAccept=COMPONENT.plain)
    box.setItem('username', None, tag='textbox', value='^.username',
                validate_nodup='adm.user.username', validate_nodup_error='Taken')
    box.setItem('email', None, tag='textbox', value='^.email', validate_exist=True, dbfield='adm.user.email')
    box.setItem('relative', None, tag='textbox', value='^.x', validate_nodup='adm.user.code',
                validate_nodup_relative='group_code')
    box.setItem('remote', None, tag='dataRemote', method='_table.dmt.sede.lookup')
    box.setItem('dynamic', None, tag='dbSelect', dbtable='dmt.sede', condition='^.cond')
    form.setItem('box', box, tag='div')
    hidden = Bag()
    hidden.setItem('rpc', None, tag='dataRpc', method=COMPONENT.admin_only)
    hidden.setItem('lookup', None, tag='dbSelect', dbtable='adm.user')
    form.setItem('admin', hidden, tag='div', __forbidden__=True)
    return form


def test_the_struct_is_recorded_and_redirected():
    form = _fields()
    recorded = collect_login_rpcs(form.nodes)
    assert recorded['methods'] == ['login_sedi', 'login_checkCode', '_table.dmt.sede.lookup']
    assert recorded['counts'] == ['adm.user.username', 'adm.user.email']
    consultorio, sede, sede_bis = recorded['dbselects']
    assert consultorio == dict(id='f0', dbtable='dmt.consultorio',
                               structure=dict(condition='$abilitato IS TRUE AND $op=:env_op',
                                              hiddenColumns='codice'),
                               params=['env_op'], pinned=dict(env_op='operatore_id'))
    assert (sede['id'], sede['params'], sede['pinned']) == ('f1', ['c'], {})
    assert sede_bis['id'] == 'f2'
    assert form.getAttr('consultorio')['method'] == 'login_fieldSelect'
    assert form.getAttr('consultorio')['condition_login_field'] == 'f0'
    username = form.getAttr('box.username')
    assert 'validate_nodup' not in username
    assert (username['validate_remote'], username['validate_login_field'], username['validate_login_check'],
            username['validate_remote_error']) == ('login_fieldCount', 'adm.user.username', 'nodup', 'Taken')
    assert form.getAttr('box.email')['validate_login_check'] == 'exist'
    assert form.getAttr('box.relative')['validate_nodup'] == 'adm.user.code'


def test_generic_app_rpcs_are_never_recorded():
    recorded = collect_login_rpcs(_fields().nodes)
    assert 'app.getSelection' not in recorded['methods']
    assert not declared_method('app.getSelection', Bag(dict(methods=['app.getSelection'])))


def test_a_field_bound_to_client_data_is_not_served():
    form = _fields()
    recorded = collect_login_rpcs(form.nodes)
    assert form.getAttr('box.dynamic').get('method') is None
    assert len(recorded['dbselects']) == 3


def test_forbidden_subtrees_are_skipped():
    form = _fields()
    recorded = collect_login_rpcs(form.nodes)
    assert rpc_name(COMPONENT.admin_only) not in recorded['methods']
    assert 'adm.user' not in [s['dbtable'] for s in recorded['dbselects']]
    assert form.getAttr('admin.lookup').get('method') is None


def test_a_second_pass_records_nothing_new():
    form = _fields()
    first = collect_login_rpcs(form.nodes)
    again = without_field_rpcs(collect_login_rpcs(form.nodes, field_prefix='p'), first)
    assert (again['methods'], again['dbselects'], again['counts']) == ([], [], [])


def test_dbselect_runs_with_the_declared_structure_and_client_values_only():
    sent = dict(dbtable='dmt.sede', login_field='f1', condition='1=1', auxColumns='$secret',
                hiddenColumns='$pwd', ignorePartition=True, subtable='*', _storename='other',
                selectmethod='app.getSelection', c='C1', _id='S1', limit=0, unexpected='x')
    assert dbselect_kwargs(collect_login_rpcs(_fields().nodes), sent) == dict(
        dbtable='dmt.sede', auxColumns='$indirizzo', condition='$consultorio_id=:c', c='C1', _id='S1', limit=0)


def test_each_field_keeps_its_own_structure():
    recorded = collect_login_rpcs(_fields().nodes)
    served = dbselect_kwargs(recorded, dict(dbtable='dmt.sede', login_field='f2', c='C1'))
    assert served['condition'] == '$consultorio_id=:c AND $principale IS TRUE'
    assert 'auxColumns' not in served


def test_dbselect_without_a_matching_field_is_refused():
    recorded = collect_login_rpcs(_fields().nodes)
    assert dbselect_kwargs(recorded, dict(dbtable='adm.user', login_field='f1')) is None
    assert dbselect_kwargs(recorded, dict(dbtable='dmt.sede')) is None
    assert dbselect_kwargs(recorded, dict(dbtable='dmt.sede', login_field='f9')) is None


def test_rootenv_parameters_come_from_the_checked_rootenv():
    recorded = collect_login_rpcs(_fields().nodes)
    rootenv = Bag(dict(operatore_id='OP1', consultorio_id='C9'))
    sent = dict(dbtable='dmt.consultorio', login_field='f0', env_op='OTHER', _querystring='*')
    assert dbselect_kwargs(recorded, sent, rootenv)['env_op'] == 'OP1'
    assert dbselect_kwargs(recorded, sent)['env_op'] == 'OTHER'


def test_a_value_chosen_in_the_form_stays_the_client_one():
    recorded = collect_login_rpcs(_fields().nodes)
    rootenv = Bag(dict(consultorio_id='C9'))
    assert dbselect_kwargs(recorded, dict(dbtable='dmt.sede', login_field='f1', c='C1'), rootenv)['c'] == 'C1'


def test_an_absolute_rootenv_path_is_pinned_too():
    form = Bag()
    form.setItem('f', None, tag='dbSelect', dbtable='erp.ufficio', condition='$staff_id=:staff_id',
                 condition_staff_id='=gnr.rootenv.staff_id')
    recorded = collect_login_rpcs(form.nodes)
    sent = dict(dbtable='erp.ufficio', login_field='f0', staff_id='X')
    assert dbselect_kwargs(recorded, sent, Bag(dict(staff_id='S1'))) \
        == dict(dbtable='erp.ufficio', condition='$staff_id=:staff_id', staff_id='S1')


def test_declared_methods_are_matched_by_exact_name():
    recorded = collect_login_rpcs(_fields().nodes)
    assert declared_method('login_sedi', recorded)
    assert declared_method('_table.dmt.sede.lookup', recorded)
    assert not declared_method('plain', recorded)
    assert not declared_method('*|other:Component;login_sedi', recorded)
    assert not declared_method('login_sedi', None)


def test_form_value_keys_are_the_fields_of_the_form():
    keys = form_value_keys(_fields().nodes)
    assert keys == ['consultorio_id', 'sede_id', 'sede_bis_id', 'code', 'username', 'email', 'x']


def test_the_login_rootenv_takes_from_the_client_only_the_form_fields():
    page = Bag(dict(language='it'))
    checked = Bag(dict(user_id='U1', operatore_id='OP1', accesso_globale=False, consultorio_id='C1'))
    sent = Bag(dict(user_id='ADMIN', operatore_id='OTHER', accesso_globale=True, user_local_tags='admin',
                    allowed_consultorio_id=['C1', 'C2'], consultorio_id='C2', workdate='2026-01-01'))
    rootenv = trusted_rootenv(page, checked, sent, ['consultorio_id', 'workdate'])
    assert rootenv.asDict() == dict(language='it', user_id='U1', operatore_id='OP1', accesso_globale=False,
                                    consultorio_id='C2', workdate='2026-01-01')


def test_without_a_checked_rootenv_nothing_reserved_comes_from_the_client():
    rootenv = trusted_rootenv(None, None, Bag(dict(user_local_tags='admin', workdate='d')), ['workdate'])
    assert rootenv.asDict() == dict(workdate='d')
