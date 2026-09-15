"""Unit tests for the ratchet mechanism both page suites assert through.

`assert_ratchet` is the only thing keeping either list honest, and the render
sweep now leans on it alone: a page leaves the checked set by being written into
`smoke_known_failures.txt` and nowhere else. A ratchet that failed in one
direction only would let that list grow unnoticed, which is the whole property
it exists to deny, so both directions are checked here.

Source-only by design: no instance, no db, no daemon. That is what lets this
suite run in CI next to `test_pages_documented.py`, while the render sweep stays
local.
"""
import pytest

from pages_ratchet import assert_ratchet, page_url, read_ratchet


def write_ratchet(tmp_path, *lines):
    """A ratchet file holding the given lines, as the committed ones look"""
    ratchet_path = tmp_path / 'ratchet.txt'
    ratchet_path.write_text('# a comment\n\n%s\n' % '\n'.join(lines), encoding='utf-8')
    return str(ratchet_path)


class TestAssertRatchet(object):
    """assert_ratchet fails in both directions and passes on an exact match"""

    def test_offender_outside_the_list(self, tmp_path):
        """An offender the list does not hold is a regression, and is named"""
        ratchet_path = write_ratchet(tmp_path, 'test/webpages/tools/flibpicker.py')
        with pytest.raises(AssertionError) as failure:
            assert_ratchet(['test/webpages/tools/flibpicker.py', 'test/webpages/html/div.py'],
                           ratchet_path, 'failing pages')
        assert 'test/webpages/html/div.py' in str(failure.value)

    def test_entry_that_no_longer_offends(self, tmp_path):
        """A list entry that stopped offending is stale, and is named

        This is the direction that makes the list shrink by itself: without it
        an entry survives its own fix and quietly keeps a page out of the check.
        """
        ratchet_path = write_ratchet(tmp_path, 'test/webpages/tools/flibpicker.py')
        with pytest.raises(AssertionError) as failure:
            assert_ratchet([], ratchet_path, 'failing pages')
        assert 'test/webpages/tools/flibpicker.py' in str(failure.value)

    def test_offenders_matching_the_list(self, tmp_path):
        """Offenders that are exactly the list are the state the ratchet allows"""
        ratchet_path = write_ratchet(tmp_path, 'test/webpages/tools/flibpicker.py')
        assert_ratchet(['test/webpages/tools/flibpicker.py'], ratchet_path, 'failing pages')

    def test_no_offenders_and_an_empty_list(self, tmp_path):
        """An empty list with nothing offending passes"""
        assert_ratchet([], write_ratchet(tmp_path), 'failing pages')

    def test_missing_ratchet_file(self, tmp_path):
        """A ratchet file that does not exist holds nothing, it does not raise"""
        missing_path = str(tmp_path / 'absent.txt')
        assert read_ratchet(missing_path) == set()
        with pytest.raises(AssertionError):
            assert_ratchet(['test/webpages/html/div.py'], missing_path, 'failing pages')


class TestReadRatchet(object):
    """read_ratchet keeps the comments the committed files carry out of the set"""

    def test_comments_and_blank_lines(self, tmp_path):
        """Only page paths are read; comments and blank lines are not entries"""
        ratchet_path = write_ratchet(tmp_path, 'test/webpages/html/div.py', '', '# another one')
        assert read_ratchet(ratchet_path) == {'test/webpages/html/div.py'}


class TestPageUrl(object):
    """page_url maps a discovered path to the url the sweep requests"""

    def test_nested_page(self):
        """The package prefix is kept and the webpages folder drops out"""
        assert page_url('test/webpages/inputfields/dbselect.py') == '/test/inputfields/dbselect'

    def test_page_at_the_root_of_the_package(self):
        """A page directly under webpages keeps its package and its name"""
        assert page_url('test15/webpages/index.py') == '/test15/index'
