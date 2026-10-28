"""An item idle for more than a day is stale, however many days (#1566).

``timedelta.seconds`` is the remainder within the day, so the old comparison
restarted from zero every 24 hours and let a day-old connection survive.
"""

from datetime import datetime, timedelta

from gnr.web.daemon.siteregister import SiteRegister


class _FakeDaemon:
    def register(self, obj, name):
        pass


class _FakeServer:
    daemon = _FakeDaemon()


def _register():
    reg = SiteRegister(_FakeServer(), sitename='t')
    reg.setConfiguration()
    reg.new_connection('c1', user='bob')
    reg.new_page('p1', pagename='p', connection_id='c1', user='bob')
    return reg


def _age(reg, register_name, item_id, hours):
    item = reg.get_register(register_name).get_item(item_id)
    item['last_refresh_ts'] = datetime.now() - timedelta(hours=hours)


def test_a_connection_idle_for_a_day_and_a_bit_is_expired():
    reg = _register()
    _age(reg, 'connection', 'c1', hours=24.2)
    assert reg.expire_connection('c1') is True


def test_a_page_idle_for_a_day_and_a_bit_is_expired():
    reg = _register()
    _age(reg, 'page', 'p1', hours=24.05)
    assert reg.expire_pages('c1') == ['p1']


def test_a_fresh_connection_survives():
    reg = _register()
    assert reg.expire_connection('c1') is False
