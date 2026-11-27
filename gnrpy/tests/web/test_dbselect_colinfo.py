"""dbSelect sends the dtype and format of its columns.

The auxColumns popup renders them through ``genro.dom.scrollableTable``,
which right-aligns and formats numeric cells only when it knows their
dtype and format.
"""

import json
import os

import pytest

from core.common import BaseGnrTest
from sql.conftest import db_sqlite, sqlite_temp_dir        # noqa: F401  (fixtures)

from apphandler_legacy_common import _StandInPage

from gnr.web.gnrwebpage_proxy.apphandler import GnrWebAppHandler


def setup_module(module):
    if not os.environ.get('GENRO_GNRFOLDER'):
        BaseGnrTest.setup_class()
        module._owns_config = True


def teardown_module(module):
    if getattr(module, '_owns_config', False):
        BaseGnrTest.teardown_class()


@pytest.fixture
def handler(db_sqlite, tmp_path):                           # noqa: F811
    return GnrWebAppHandler(_StandInPage(db_sqlite, str(tmp_path)))


def test_dbselect_result_carries_colinfo(handler):
    result, attrs = handler.dbSelect(dbtable='invc.customer', columns='$account_name',
                                     querystring='a', limit=1)
    colinfo = json.loads(attrs['colinfo'])
    assert len(colinfo) == len(attrs['columns'].split(','))
    assert set(colinfo[0]) == {'dtype', 'format'}


@pytest.mark.parametrize('colattr,expected', [
    ({'dataType': 'N', 'format': '#,##0.00'}, {'dtype': 'N', 'format': '#,##0.00'}),
    ({'dataType': 'money', 'format': '#,##0.00'}, {'dtype': 'N', 'format': '#,##0.00'}),
    ({'dataType': 'M'}, {'dtype': 'N', 'format': None}),
    ({'dataType': 'T'}, {'dtype': 'T', 'format': None}),
])
def test_colinfo_maps_money_to_numeric(handler, colattr, expected):
    assert handler._dbSelectColInfo(colattr) == expected
