"""Cross-language RPC envelope and parameter transport regressions."""
from decimal import Decimal
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest
from genro_bag import Bag
from genro_tytx import from_tytx
from gnr.web.gnrbagtransport import encode_envelope, transport_format
from gnr.web.gnrwebpage_proxy.rpc import GnrWebRpc


class Application:
    config = SimpleNamespace(getItem=lambda path: "fetch")

    def __init__(self, **settings):
        self.settings = settings

    def experimentalValue(self, group, name):
        return self.settings.get(group)


def test_configuration_requires_both_new_implementations():
    assert transport_format(Application()) == 'xml'
    with pytest.raises(ValueError):
        transport_format(Application(bag_transport='tytx'))
    assert transport_format(Application(bag_transport='tytx', bag='genro-bag',
                                       bag_js='genro-bag-js-mixin')) == 'tytx'


def test_python_envelope_is_read_by_actual_browser_bundle():
    envelope = Bag()
    envelope.set_item(
        'result',
        Bag({'text': 'literal::T', 'zero': 0, 'empty': Bag(),
             'decimal': Decimal('12.30'), 'decimal_zero': Decimal('0')}),
        _attributes={'__cls': 'domsource',
                     'nested': {'amount': Decimal('3.50')}})
    payload = encode_envelope(envelope, lambda value: value)
    root = Path(__file__).resolve().parents[3]
    script = r'''
const {loadClasses} = require('./gnrjs/tests/bag_audit_harness.cjs');
const c = loadClasses(['gnrlang.js','genro_bagjs_bundle.js','gnrbag_mixin.js','gnrdomsource.js']);
const bag = new c.gnr.GnrBag();
bag.fromTytxDoc(process.argv[1], {domsource:c.gnr.GnrDomSource});
if (!(bag.getItem('result') instanceof c.gnr.GnrDomSource)) throw Error('wrong class');
if (bag.getItem('result.text') !== 'literal') throw Error('text corruption');
if (typeof bag.getItem('result.decimal') !== 'number' || bag.getItem('result.decimal') + 1 !== 13.3) throw Error('decimal value');
if (typeof bag.getItem('result.decimal_zero') !== 'number' || bag.getItem('result.decimal_zero') !== 0) throw Error('decimal zero');
if (typeof bag.getNode('result').attr.nested.amount !== 'number' || bag.getNode('result').attr.nested.amount < 3) throw Error('decimal attribute');
process.stdout.write(bag.toTytxParameter());
'''
    result = subprocess.run(['node', '-e', script, payload.decode()], cwd=root,
                            capture_output=True, text=True, check=True)
    suffix = '::BAGTYTX'
    assert result.stdout.endswith(suffix)
    restored = Bag.from_tytx(result.stdout[:-len(suffix)], transport='json')
    assert restored['result.text'] == 'literal'
    assert restored['result.zero'] == 0
    assert isinstance(restored['result.empty'], Bag)


def test_envelope_encoder_uses_genropy_adapter_rows():
    envelope = Bag()
    envelope.set_item('result', '!!Localized', _attributes={'caption': '!!Caption'})
    payload = encode_envelope(envelope, lambda value: 'L:' + value)
    decoded = from_tytx(payload.decode(), transport=None)
    assert decoded == {'rows': [
        ['', 'result', None, 'L:!!Localized', {'caption': 'L:!!Caption'}]
    ]}


def test_shared_result_bag_builds_complete_tytx_envelope():
    application = Application(bag_transport='tytx', bag='genro-bag',
                              bag_js='genro-bag-js-mixin')
    changes = Bag({'changed': 1})
    page = SimpleNamespace(
        application=application,
        response=SimpleNamespace(content_type=None),
        domSrcFactory=type('DomSource', (), {}),
        isLocalizer=lambda: False,
        localize=lambda value: value,
        collectClientDatachanges=lambda: changes,
        setInClientData=lambda value: None,
        _closed=False,
        _subscribe_event=lambda *args: None,
    )
    proxy = GnrWebRpc(page)
    proxy.error = 'test error'
    payload = proxy.result_bag((Bag({'answer': 42}), {'caption': 'Result'}))
    rows = from_tytx(payload.decode(), transport=None)['rows']
    by_path = {(parent, label): (value, attr)
               for parent, label, _tag, value, attr in rows}
    assert by_path[('', 'resultType')][0] == 'node'
    assert by_path[('', 'error')][0] == 'test error'
    assert by_path[('', 'result')][1] == {'caption': 'Result'}
    assert by_path[('result', 'answer')][0] == 42
    assert by_path[('dataChanges', 'changed')][0] == 1


@pytest.mark.parametrize('reference', ['getPageStoreData', 'app.getRecord', 'pkg|component;load'])
def test_returned_opaque_rpc_reference_is_a_name_not_a_python_method(reference):
    from gnr.core.gnrclasses import GnrClassCatalog
    from gnr.web.gnrwsgisite import GnrWsgiSite
    application = Application(bag_transport='tytx', bag='genro-bag',
                              bag_js='genro-bag-js-mixin')
    application.catalog = GnrClassCatalog()
    site = SimpleNamespace(gnrapp=application)
    result = GnrWsgiSite.parse_kwargs(site, {'method': reference + '::RPC', 'count': '2::L'})
    assert result == {'method': reference, 'count': 2}
    assert not callable(result['method'])


def test_menu_resolver_uses_portable_description_without_serializing_page():
    from gnr.web.gnrmenu import MenuResolver
    page = object()
    resolver = MenuResolver(_page=page, xmlresolved=False)
    bag = Bag()
    bag.set_item('menu', resolver)
    payload = bag.to_genropy_js()
    import json
    marker = payload['rows'][0][3]
    assert marker.startswith('::RSLV:')
    description = json.loads(marker[len('::RSLV:'):])
    assert description['resolver_class'] == 'MenuResolver'
    assert '_page' not in description['kwargs']
    assert bag.get_node('menu').resolver is resolver
    encode_envelope(bag, lambda text: text)


def test_unbound_rpc_function_uses_method_name_not_function_repr():
    def rpc_query():
        pass
    bag = Bag()
    bag.set_item('method', rpc_query)
    assert bag.to_genropy_js()['rows'][0][3] == 'query::RPC'


def test_internal_callable_attributes_are_not_exported_as_rpc_methods():
    def internal_hook():
        pass
    def rpc_public():
        pass
    bag = Bag()
    bag.set_item('query', None, _attributes={'applymethod': internal_hook, 'method': rpc_public})
    attrs = bag.to_genropy_js()['rows'][0][4]
    assert 'applymethod' not in attrs
    assert attrs['method'] == 'public::RPC'


def test_tytx_requires_fetch_switch():
    app = Application(bag_transport='tytx', bag='genro-bag',
                      bag_js='genro-bag-js-mixin')
    app.config = SimpleNamespace(getItem=lambda path: None)
    with pytest.raises(ValueError, match='fetch'):
        transport_format(app)


def test_serialization_uses_existing_bag_without_rebuilding_nodes(monkeypatch):
    bag = Bag({'branch': Bag({'leaf': '!!Text'})})
    bag.set_item('hidden', Bag({'secret': 'private'}), _attributes={'__forbidden__': True})
    bag.set_item('visible', 42)
    def reject(*args, **kwargs):
        raise AssertionError('serialization must not construct an intermediate Bag')
    monkeypatch.setattr(Bag, '__init__', reject)
    rows = bag.to_genropy_js(lambda text: 'L:' + text)['rows']
    assert [(r[0], r[1], r[3]) for r in rows] == [
        ('', 'branch', '::X'), ('branch', 'leaf', 'L:!!Text'), ('', 'visible', 42)]


@pytest.mark.parametrize('resolver_name', ['SqlRelatedRecordResolver', 'SqlRelatedSelectionResolver'])
def test_sql_resolver_legacy_serialization_is_bridged_with_deprecation(resolver_name):
    import json
    from gnr.sql.gnrsqldata import record
    resolver = getattr(record, resolver_name)(db=object(), target_fld='invc.customer.id', output_mode='bag')
    bag = Bag()
    bag.set_item('relation', resolver)
    with pytest.warns(DeprecationWarning, match='move the serialization override'):
        payload = encode_envelope(bag, lambda text: text)
    marker = from_tytx(payload.decode(), transport=None)['rows'][0][3]
    description = json.loads(marker[len('::RSLV:'):])
    assert description['resolver_class'] == resolver_name
    assert description['kwargs']['_serialized_app_db'] == 'maindb'
    assert description['kwargs']['output_mode'] == 'bag'
    assert 'mode' not in description['kwargs']
    assert 'db' not in description['kwargs']
    assert resolver.db is not None


def test_legacy_serialization_super_call_does_not_recurse_and_modern_override_wins():
    from genro_bag import BagResolver
    class Legacy(BagResolver):
        def resolverSerialize(self):
            result = super().resolverSerialize()
            result['kwargs']['custom'] = 'kept'
            return result
    with pytest.warns(DeprecationWarning):
        result = Legacy().serialize()
    assert result['kwargs']['custom'] == 'kept'
    assert result['resolver_class'] == 'Legacy'
    class Modern(Legacy):
        def serialize(self):
            return {'modern': True}
    assert Modern().serialize() == {'modern': True}


def test_page_asset_choice_controls_rpc_envelope_on_same_server():
    app = Application(bag_transport='tytx', bag='genro-bag',
                      bag_js='genro-bag-js-mixin')
    assert transport_format(app, page=SimpleNamespace(application=app)) == 'tytx'
    assert transport_format(app, page=SimpleNamespace(
        application=app, bag_js_implementation='legacy')) == 'xml'
    assert transport_format(app, page=SimpleNamespace(
        application=app, page_frontend='bag_native')) == 'xml'
    assert transport_format(app) == 'tytx'


def test_incoming_tytx_parameter_decodes_with_transport_enabled():
    from gnr.core.gnrclasses import GnrClassCatalog
    from gnr.web.gnrwsgisite import GnrWsgiSite
    application = Application(bag_transport='tytx', bag='genro-bag',
                              bag_js='genro-bag-js-mixin')
    application.catalog = GnrClassCatalog()
    payload = Bag({'answer': 42}).to_tytx(transport='json') + '::BAGTYTX'
    result = GnrWsgiSite.parse_kwargs(SimpleNamespace(gnrapp=application), {'data': payload})
    assert isinstance(result['data'], Bag)
    assert result['data']['answer'] == 42
