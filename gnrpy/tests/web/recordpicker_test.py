from pathlib import Path
from types import SimpleNamespace

import pytest

from core.common import BaseGnrAppTest
from gnr.core.gnrlang import gnrImport
from gnr.web.gnrwebpage_proxy.apphandler.db_select import DbSelectMixin
from gnr.web.gnrwebstruct import GnrDomSrc_dojo_11
from web.gnrwebstruct_test import _PageStub


RESOURCE = Path(__file__).resolve().parents[3] / 'resources/common/gnrcomponents/recordpicker/recordpicker.py'
RecordPicker = gnrImport(str(RESOURCE)).RecordPicker


class PickerPage(RecordPicker, _PageStub):
    pass


def make_picker(**kwargs):
    page = PickerPage()
    root = GnrDomSrc_dojo_11.makeRoot(page)
    return page.rp_recordPicker(root, **kwargs)


def test_local_picker_contract():
    root = make_picker(checkedId='^.keys', storepath='.customers', multiSelect=True,
                       preview=True, template='<b>$caption</b>', selectedRecord='^.records')
    config = root.attributes['picker_config']
    assert config['multiSelect'] is True
    assert config['showRadio'] is False
    assert config['showSelected'] is True
    assert 'onConfirm' not in config
    assert not hasattr(RecordPicker, 'rp_recordPickerDialog')
    assert config['selectedRecord'] == '^.records'
    assert config['template'] == '<b>$caption</b>'
    controllers = [node.attr for node in root if node.attr.get('tag') == 'dataController']
    assert any(c.get('checkedId') == '^.keys' for c in controllers)
    assert any(c.get('store') == '^.customers' for c in controllers)


@pytest.mark.parametrize('multiple, explicit, expected', [
    (False, None, False), (True, None, True), (False, True, True), (True, False, False)
])
def test_selected_summary_is_optional(multiple, explicit, expected):
    root = make_picker(checkedId='^.keys', storepath='.rows',
                       multiSelect=multiple, showSelected=explicit)
    assert root.attributes['picker_config']['showSelected'] is expected


def test_record_button_placeholder_and_template():
    page = PickerPage()
    root = GnrDomSrc_dojo_11.makeRoot(page)
    button = page.rp_recordPickerButton(root, record='^.record', placeholder='!!Select province',
                                       template='<b>$nome</b>', action="genro.publish('open_picker');")
    assert button.attributes['tag'] == 'button'
    assert button.attributes['iconRight'] is True
    assert button.attributes['action'] == "genro.publish('open_picker');"
    controllers = [node.attr for node in button if node.attr.get('tag') == 'dataController']
    assert any(c.get('record') == '^.record' and c.get('placeholder') == '!!Select province'
               and c.get('template') == '<b>$nome</b>' for c in controllers)


def test_fixed_box_and_explicit_columns():
    root = make_picker(checkedId='^.keys', storepath='.rows', cols=3, boxHeight='240px',
                       emptyMessage='!!No items')
    config = root.attributes['picker_config']
    assert config['cols'] == 3
    assert config['boxHeight'] == '240px'
    assert config['emptyMessage'] == '!!No items'


def test_condition_parameters_preserve_reactive_bindings():
    root = make_picker(checkedId='^.key', table='invc.payment_type',
                       condition='$code=:code', condition_code='^.code')
    controllers = [node.attr for node in root if node.attr.get('tag') == 'dataController']
    assert any(c.get('condition_code') == '^.code' for c in controllers)


@pytest.mark.parametrize('kwargs', [
    dict(checkedId='.key', storepath='.rows'),
    dict(checkedId='^.key'),
    dict(checkedId='^.key', table='invc.payment_type', storepath='.rows'),
    dict(checkedId='^.key', storepath='.rows', limit=0),
    dict(checkedId='^.key', storepath='.rows', maxSelect=0),
    dict(checkedId='^.key', storepath='.rows', layout='unknown'),
    dict(checkedId='^.key', storepath='.rows', cols=0),
    dict(checkedId='^.key', storepath='.rows', cols=2.5),
    dict(checkedId='^.key', storepath='.rows', boxHeight=-1),
])
def test_invalid_configuration_fails_early(kwargs):
    with pytest.raises(ValueError):
        make_picker(**kwargs)


class TestPickerDatabaseContract(BaseGnrAppTest):
    app_name = 'test_invoice'

    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.app.db.model.check(applyChanges=True)
        for code, description in [('A', 'Rossi Milan'), ('B', 'Rossi Bergamo'), ('C', 'Verde Casa')]:
            cls.app.db.table('invc.payment_type').insert(dict(code=code, description=description))
        cls.app.db.commit()

    def test_empty_message_localization(self):
        assert self.app.localizer.translate('!!No items', language='it') == 'Nessun elemento'
        assert self.app.localizer.translate('!!No items', language='en') == 'No items'

    def handler(self):
        handler = DbSelectMixin()
        handler.db = self.app.db
        handler.gnrapp = self.app
        handler.page = SimpleNamespace(locale='en', _=lambda text: text)
        return handler

    def query(self, **kwargs):
        return self.handler().dbSelect(dbtable='invc.payment_type',
                                      columns='$description,$code', hiddenColumns='$description,$code',
                                      notnull=True, weakCondition=False, **kwargs)[0]

    def test_search_returns_templates_fields_and_stable_identifiers(self):
        rows = self.query(_querystring='Rossi', limit=30)
        assert {node.attr['_pkey'] for node in rows} == {'A', 'B'}
        assert {node.attr['description'] for node in rows} == {'Rossi Milan', 'Rossi Bergamo'}

    def test_preselection_hydration_respects_conditions(self):
        rows = self.query(_querystring='*', limit=2,
                          condition='($code=:allowed) AND $pkey IN :_picker_keys',
                          allowed='B', _picker_keys=['A', 'B'])
        assert [node.attr['_pkey'] for node in rows] == ['B']

    def test_limit_and_empty_search(self):
        assert len(self.query(_querystring='*', limit=2)) == 2
        assert len(self.query(_querystring='No matching customer', limit=2)) == 0
