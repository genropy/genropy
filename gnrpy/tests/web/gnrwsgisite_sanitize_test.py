"""Tests for XSS sanitization logic in GnrWsgiSite.

These tests exercise _sanitize_string and sanitize_request_params directly
without starting a daemon or initialising the full site stack. The methods
are pure regex logic that operate on _XSS_PATTERNS and have no side-effects.
"""

import pytest

import gnr.web.gnrwsgisite as gws
from gnr.web.gnrwsgisite import GnrWsgiSite, _XSS_PATTERNS


# ---------------------------------------------------------------------------
# Minimal stub: bypass __init__ (no config / db needed)
# ---------------------------------------------------------------------------

@pytest.fixture
def site():
    """Return an uninitialised GnrWsgiSite instance sufficient for sanitization tests."""
    return GnrWsgiSite.__new__(GnrWsgiSite)


# ---------------------------------------------------------------------------
# _sanitize_string – individual pattern coverage
# ---------------------------------------------------------------------------

class TestSanitizeString:

    def test_clean_string_unchanged(self, site):
        assert site._sanitize_string('hello world') == 'hello world'

    def test_empty_string(self, site):
        assert site._sanitize_string('') == ''

    def test_removes_script_block(self, site):
        payload = '<script>alert("xss")</script>'
        result = site._sanitize_string(payload)
        assert '<script>' not in result.lower()
        assert 'alert' not in result

    def test_removes_script_block_multiline(self, site):
        payload = '<script>\nalert("xss")\n</script>'
        result = site._sanitize_string(payload)
        assert '<script>' not in result.lower()

    def test_removes_script_block_case_insensitive(self, site):
        payload = '<SCRIPT>alert(1)</SCRIPT>'
        result = site._sanitize_string(payload)
        assert 'script' not in result.lower()

    def test_removes_open_script_tag(self, site):
        payload = '<script src="evil.js">'
        result = site._sanitize_string(payload)
        assert '<script' not in result.lower()

    def test_removes_javascript_uri(self, site):
        payload = 'javascript:alert(1)'
        result = site._sanitize_string(payload)
        assert 'javascript:' not in result.lower()

    def test_removes_javascript_uri_with_spaces(self, site):
        payload = 'java script : alert(1)'
        result = site._sanitize_string(payload)
        assert 'javascript' not in result.lower()

    def test_removes_vbscript_uri(self, site):
        payload = 'vbscript:msgbox("xss")'
        result = site._sanitize_string(payload)
        assert 'vbscript:' not in result.lower()

    def test_removes_event_handler_double_quotes(self, site):
        payload = '<img src="x" onerror="alert(1)">'
        result = site._sanitize_string(payload)
        assert 'onerror=' not in result.lower()

    def test_removes_event_handler_single_quotes(self, site):
        payload = "<a onclick='evil()'>click</a>"
        result = site._sanitize_string(payload)
        assert 'onclick=' not in result.lower()

    def test_removes_onload_handler(self, site):
        payload = '<body onload="steal()">'
        result = site._sanitize_string(payload)
        assert 'onload=' not in result.lower()

    def test_removes_iframe(self, site):
        payload = '<iframe src="http://evil.example.com"></iframe>'
        result = site._sanitize_string(payload)
        assert '<iframe' not in result.lower()

    def test_removes_iframe_closing_tag(self, site):
        payload = '</iframe>'
        result = site._sanitize_string(payload)
        assert '</iframe>' not in result.lower()

    def test_combined_payload(self, site):
        payload = '<script>document.location="javascript:void(0)"</script><iframe src="x">'
        result = site._sanitize_string(payload)
        assert '<script' not in result.lower()
        assert 'javascript:' not in result.lower()
        assert '<iframe' not in result.lower()

    def test_preserves_plain_html_without_vectors(self, site):
        payload = '<p>Hello <b>world</b></p>'
        result = site._sanitize_string(payload)
        assert '<p>' in result
        assert '<b>' in result

    def test_numeric_value_as_string(self, site):
        assert site._sanitize_string('42') == '42'

    def test_unicode_text_unchanged(self, site):
        payload = 'Ciao Ünivërsò'
        assert site._sanitize_string(payload) == payload


# ---------------------------------------------------------------------------
# sanitize_request_params – dict handling
# ---------------------------------------------------------------------------

class TestSanitizeRequestParams:

    def test_clean_dict_unchanged(self, site):
        params = {'name': 'Alice', 'age': 30}
        result = site.sanitize_request_params(params)
        assert result == params

    def test_sanitizes_string_values(self, site):
        params = {'comment': '<script>evil()</script>'}
        result = site.sanitize_request_params(params)
        assert '<script>' not in result['comment'].lower()

    def test_preserves_non_string_values(self, site):
        params = {'count': 5, 'ratio': 3.14, 'flag': True}
        result = site.sanitize_request_params(params)
        assert result['count'] == 5
        assert result['ratio'] == 3.14
        assert result['flag'] is True

    def test_sanitizes_list_of_strings(self, site):
        params = {'tags': ['safe', '<script>bad()</script>', 'also safe']}
        result = site.sanitize_request_params(params)
        assert result['tags'][0] == 'safe'
        assert '<script>' not in result['tags'][1].lower()
        assert result['tags'][2] == 'also safe'

    def test_preserves_non_string_items_in_list(self, site):
        params = {'ids': [1, 2, 3]}
        result = site.sanitize_request_params(params)
        assert result['ids'] == [1, 2, 3]

    def test_mixed_list(self, site):
        params = {'mixed': [1, '<script>x</script>', 'clean']}
        result = site.sanitize_request_params(params)
        assert result['mixed'][0] == 1
        assert '<script>' not in result['mixed'][1].lower()
        assert result['mixed'][2] == 'clean'

    def test_empty_dict(self, site):
        assert site.sanitize_request_params({}) == {}

    def test_empty_string_value(self, site):
        params = {'key': ''}
        result = site.sanitize_request_params(params)
        assert result['key'] == ''

    def test_multiple_keys_sanitized_independently(self, site):
        params = {
            'a': 'javascript:alert(1)',
            'b': 'safe value',
            'c': '<iframe src="x">',
        }
        result = site.sanitize_request_params(params)
        assert 'javascript:' not in result['a'].lower()
        assert result['b'] == 'safe value'
        assert '<iframe' not in result['c'].lower()

    def test_returns_new_dict_not_in_place(self, site):
        params = {'x': '<script>a()</script>'}
        result = site.sanitize_request_params(params)
        # Original must be untouched
        assert params['x'] == '<script>a()</script>'
        assert result is not params


# ---------------------------------------------------------------------------
# _XSS_PATTERNS module constant
# ---------------------------------------------------------------------------

def test_xss_patterns_is_non_empty():
    assert len(_XSS_PATTERNS) > 0


def test_xss_patterns_are_compiled():
    import re
    for p in _XSS_PATTERNS:
        assert hasattr(p, 'sub'), f"Pattern {p!r} is not a compiled regex"
