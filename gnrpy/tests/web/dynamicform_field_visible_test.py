from pathlib import Path

import pytest

from gnr.core.gnrlang import gnrImport
from gnr.web.gnrwebstruct import GnrDomSrc


@pytest.fixture
def dynamicform():
    saved = GnrDomSrc._external_methods.copy()
    resource = Path(__file__).resolve().parents[3] / 'resources/common/gnrcomponents/dynamicform/dynamicform.py'
    component = gnrImport(str(resource))
    yield component.DynamicForm.__new__(component.DynamicForm)
    GnrDomSrc._external_methods.clear()
    GnrDomSrc._external_methods.update(saved)


FIELDS = [dict(code='liti'), dict(code='liti_calc')]


def test_hidden_input_field_is_reset(dynamicform):
    attr = dict(code='liti_text', field_visible='liti')
    dynamicform._df_handleFieldValidation(attr, fields=FIELDS)
    assert "sourceNode.setRelativeData('.liti_text',null);" in attr['hidden']


def test_hidden_calculated_field_keeps_its_formula_value(dynamicform):
    attr = dict(code='liti_calc', field_visible='!liti')
    dynamicform._df_handleFieldValidation(attr, fields=FIELDS, calculated=True)
    assert "setRelativeData('.liti_calc',null)" not in attr['hidden']


def test_mandatory_hidden_field_still_toggles_validation(dynamicform):
    attr = dict(code='liti_text', field_visible='liti', mandatory=True)
    dynamicform._df_handleFieldValidation(attr, fields=FIELDS)
    assert "setRelativeData('#WORKSPACE.liti_text.do_validations',false);" in attr['hidden']
    assert "sourceNode.setRelativeData('.liti_text',null);" in attr['hidden']
