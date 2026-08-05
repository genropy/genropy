from gnr.lib.services.llm import LlmService


class MockParent:
    pass


def test_resolve_model_none_returns_default():
    svc = LlmService(parent=MockParent(), model='claude-sonnet')
    assert svc.resolve_model(None) == 'claude-sonnet'


def test_resolve_model_configured_alias():
    svc = LlmService(parent=MockParent(), model='claude-sonnet',
                     model_low='claude-haiku', model_max='claude-opus')
    assert svc.resolve_model('low') == 'claude-haiku'
    assert svc.resolve_model('max') == 'claude-opus'


def test_resolve_model_unconfigured_alias_falls_back_to_default():
    svc = LlmService(parent=MockParent(), model='claude-sonnet',
                     model_low=None, model_max='claude-opus')
    assert svc.resolve_model('low') == 'claude-sonnet'
    assert svc.resolve_model('medium') == 'claude-sonnet'


def test_resolve_model_literal_name_passthrough():
    svc = LlmService(parent=MockParent(), model='claude-sonnet')
    assert svc.resolve_model('gpt-4') == 'gpt-4'
