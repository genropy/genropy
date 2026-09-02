"""The freeze round trip: dump the three registers, load them back.

``dump`` writes the pickle with ``'wb'``. ``load`` opened the same file without a
mode, which is text, so ``pickle.load`` hit ``UnicodeDecodeError`` on the first
byte of the protocol header -- and the ``try`` around it catches ``EOFError``
only, so the exception left the site register unable to start.

The branch was reachable but rarely taken: ``start`` turns autorestore off unless
the freeze file exists, and it is only written when the daemon is stopped with
``savestatus``. These tests take it every time.
"""

import pytest

from gnr.web.daemon.siteregister import SiteRegister


class _FakeDaemon:
    def register(self, obj, name):
        pass


class _FakeServer:
    daemon = _FakeDaemon()
    gnr_daemon_uri = None
    hmac_key = None


def _register(tmp_path, name='register.pik'):
    reg = SiteRegister(_FakeServer(), sitename='testsite')
    reg.setConfiguration()
    reg.storage_path = str(tmp_path / name)
    return reg


def _populate(reg, users=2, connections=2, pages=2):
    for u in range(users):
        user = 'user-%d' % u
        for c in range(connections):
            connection_id = '%s/conn-%d' % (user, c)
            reg.new_connection(connection_id, user=user)
            for p in range(pages):
                reg.new_page('%s/page-%d' % (connection_id, p), pagename='p',
                             connection_id=connection_id, user=user)
    return reg


def _round_trip(reg, tmp_path):
    reg.dump()
    restored = _register(tmp_path)
    assert restored.load() is True
    return restored


def test_a_dumped_register_loads_back(tmp_path):
    reg = _populate(_register(tmp_path))
    restored = _round_trip(reg, tmp_path)
    assert (restored.page_register.registerItems.keys()
            == reg.page_register.registerItems.keys())
    assert (restored.connection_register.registerItems.keys()
            == reg.connection_register.registerItems.keys())
    assert (restored.user_register.registerItems.keys()
            == reg.user_register.registerItems.keys())


def test_an_empty_register_loads_back(tmp_path):
    restored = _round_trip(_register(tmp_path), tmp_path)
    assert restored.page_register.registerItems == {}


def test_the_restored_items_keep_their_parent(tmp_path):
    reg = _populate(_register(tmp_path), users=1, connections=1, pages=2)
    restored = _round_trip(reg, tmp_path)
    page = restored.page_register.registerItems['user-0/conn-0/page-0']
    assert page['connection_id'] == 'user-0/conn-0'
    assert restored.connection_register.registerItems['user-0/conn-0']['user'] == 'user-0'


def test_the_restored_register_still_drops(tmp_path):
    reg = _populate(_register(tmp_path), users=1, connections=1, pages=2)
    restored = _round_trip(reg, tmp_path)
    restored.drop_page('user-0/conn-0/page-0')
    assert restored.connection_page_keys('user-0/conn-0') == ['user-0/conn-0/page-1']


def test_the_freeze_file_is_consumed_by_the_load(tmp_path):
    """Renamed to *_loaded.pik, so a restart cannot restore the same state twice."""
    import os
    reg = _populate(_register(tmp_path), users=1, connections=1, pages=1)
    restored = _round_trip(reg, tmp_path)
    assert not os.path.exists(restored.storage_path)
    assert os.path.exists(restored.storage_path.replace('.pik', '_loaded.pik'))


def test_loading_a_missing_file_is_not_a_crash(tmp_path):
    reg = _register(tmp_path, name='never-written.pik')
    with pytest.raises(FileNotFoundError):
        reg.load()
