import pytest

from gnr.web.gnrwebpage_proxy.frontend.dojo_11 import GnrWebFrontend


class FakeApplication:
    def __init__(self, implementation=None):
        self.implementation = implementation

    def experimentalValue(self, group, name):
        assert (group, name) == ('bag_js', 'implementation')
        return self.implementation


def frontend(implementation=None):
    result = GnrWebFrontend.__new__(GnrWebFrontend)
    result.page = type('Page', (), {'application': FakeApplication(implementation)})()
    return result


@pytest.mark.parametrize('implementation', [None, 'legacy'])
def test_legacy_bag_is_the_default(implementation):
    imports = frontend(implementation).gnrjs_frontend()
    assert imports[:2] == ['gnrbag', 'gnrdomsource']
    assert 'genro_bagjs_bundle' not in imports


def test_genro_bag_js_bundle_and_adapter_precede_consumers():
    imports = frontend('genro-bag-js').gnrjs_frontend()
    assert imports[:3] == ['genro_bagjs_bundle', 'gnrbag_genro', 'gnrdomsource']
    assert 'gnrbag' not in imports


def test_unknown_bag_implementation_fails_explicitly():
    with pytest.raises(ValueError, match='Unsupported JavaScript Bag implementation: unknown'):
        frontend('unknown').gnrjs_frontend()



def test_lightweight_mixin_is_separate_from_the_reserve_adapter():
    imports = frontend('genro-bag-js-mixin').gnrjs_frontend()
    assert imports[:3] == ['genro_bagjs_bundle', 'gnrbag_mixin', 'gnrdomsource']
    assert 'gnrbag_genro' not in imports
    assert 'gnrbag' not in imports

