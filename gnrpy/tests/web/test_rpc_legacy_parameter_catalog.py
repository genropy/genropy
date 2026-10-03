"""Disabled TYTX transport preserves the legacy parameter catalog dispatch."""
from types import SimpleNamespace

import pytest

from gnr.core.gnrclasses import GnrClassCatalog
from gnr.web.gnrwsgisite import GnrWsgiSite


@pytest.mark.parametrize('setting', [None, 'xml'])
@pytest.mark.parametrize('suffix', ['RPC', 'BAGTYTX'])
def test_disabled_transport_uses_registered_catalog_parser(setting, suffix):
    catalog = GnrClassCatalog()
    calls = []

    def parser(value):
        calls.append(value)
        return {'decoded_by_catalog': value}

    catalog.parsers[suffix] = parser
    application = SimpleNamespace(catalog=catalog,
                                  experimentalValue=lambda group, name: setting)
    result = GnrWsgiSite.parse_kwargs(SimpleNamespace(gnrapp=application),
                                     {' method ': 'abc::' + suffix, 'count': '2::L'})
    assert result == {'method': {'decoded_by_catalog': 'abc'}, 'count': 2}
    assert calls == ['abc']


@pytest.mark.parametrize('suffix,error', [('RPC', TypeError), ('BAGTYTX', KeyError)])
def test_disabled_transport_preserves_standard_catalog_errors(suffix, error):
    application = SimpleNamespace(catalog=GnrClassCatalog(),
                                  experimentalValue=lambda group, name: None)
    with pytest.raises(error):
        GnrWsgiSite.parse_kwargs(SimpleNamespace(gnrapp=application),
                                {'method': 'abc::' + suffix})
