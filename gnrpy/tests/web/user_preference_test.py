"""Real checks on the site user preference accessors (#1646).

``getUserPreference``/``setUserPreference`` run against the ``gnrtest``
instance with no current page, as they do in batches, services and tasks.

Writes are checked on the ``adm.user`` record: on a dummy site the preference
cache is never invalidated (its register store drops writes), so each user
is read back through the accessor at most once.
"""

from core.common import BaseGnrTest

from gnr.app.gnrapp import GnrApp
from gnr.web.gnrdummysite import GnrDummySite

EXPLICIT_USER = 'pref1646_explicit'
PAGE_USER = 'pref1646_page'


class TestUserPreference(BaseGnrTest):

    @classmethod
    def setup_class(cls):
        super().setup_class()
        app = GnrApp(cls.test_instance_name)
        app.db.model.check(applyChanges=True)
        app.db.commit()
        cls.site = GnrDummySite(cls.test_instance_name, site_name=cls.test_instance_name)
        cls.usertbl = cls.site.db.table('adm.user')
        cls.usertbl.deleteSelection(where='$username IN :users', users=[EXPLICIT_USER, PAGE_USER])
        for username in (EXPLICIT_USER, PAGE_USER):
            cls.usertbl.insert(dict(username=username, email=f'{username}@test.local',
                                    md5pwd='secret', status='conf'))
        cls.site.db.commit()

    def setup_method(self):
        self.site.currentPage = None

    def _stored(self, username, path):
        return self.usertbl.record(username=username).output('bag')['preferences.%s' % path]

    def test_explicit_username_without_page(self):
        self.site.setUserPreference('colour', 'red', pkg='adm', username=EXPLICIT_USER)
        assert self._stored(EXPLICIT_USER, 'adm.colour') == 'red'
        assert self.site.getUserPreference('colour', pkg='adm', username=EXPLICIT_USER) == 'red'

    def test_no_username_without_page(self):
        assert self.site.getUserPreference('colour', pkg='adm', dflt='none') == 'none'
        self.site.setUserPreference('shape', 'round', pkg='adm')
        assert self._stored(EXPLICIT_USER, 'adm.shape') is None
        assert self._stored(PAGE_USER, 'adm.shape') is None

    def test_page_user_is_the_fallback(self):
        page = self.site.dummyPage
        page.user = PAGE_USER
        self.site.currentPage = page
        self.site.setUserPreference('size', 'L', pkg='adm')
        assert self._stored(PAGE_USER, 'adm.size') == 'L'
        assert self.site.getUserPreference('size', pkg='adm') == 'L'
        assert self.site.getUserPreference('size', pkg='adm', username='nobody1646',
                                           dflt='none') == 'none'
