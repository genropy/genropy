"""Batch refresh of menu line badges (#1874).

The badges are computed by the real ``menu.getMenuLineBadges`` of the headless
page of the ``gnrtest`` instance, against real ``adm.htmltemplate`` records.
"""

from core.common import BaseGnrTest

from gnr.app.gnrapp import GnrApp
from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method
from gnr.web.gnrdummysite import GnrDummySite

TABLE = 'adm.htmltemplate'


class TestMenuLineBadges(BaseGnrTest):

    @classmethod
    def setup_class(cls):
        super().setup_class()
        app = GnrApp(cls.test_instance_name)
        app.db.model.check(applyChanges=True)
        app.db.commit()
        cls.site = GnrDummySite(cls.test_instance_name, site_name=cls.test_instance_name)
        cls.page = cls.site.dummyPage
        cls.tblobj = cls.site.db.table(TABLE)
        cls.tblobj.deleteSelection(where='$id IS NOT NULL')
        for name in ('day_1', 'day_2', 'day_3'):
            cls.tblobj.insert(dict(name=name))
        cls.tblobj.insert(dict(name=None))
        cls.site.db.commit()

    def _badges(self, *lines):
        badges = Bag()
        for idx, kwargs in enumerate(lines):
            badges[f'r_{idx}'] = Bag(kwargs)
        return badges

    def test_batch_matches_single_calls(self):
        lines = [dict(table=TABLE, handler='#'),
                 dict(table=TABLE, handler='#:name'),
                 dict(table=TABLE, handler='#:!name')]
        result = self.page.menu.getMenuLineBadges(badges=self._badges(*lines))
        assert list(result.keys()) == ['r_0', 'r_1', 'r_2']
        assert result['r_0'] == 4
        assert result['r_1'] == 3
        assert result['r_2'] == 1
        for idx, kwargs in enumerate(lines):
            assert result[f'r_{idx}'] == self.page.menu.getMenuLineBadge(**kwargs)

    def test_handler_lines_share_one_request(self, monkeypatch):
        page = self.page
        computed = []

        @public_method
        def checklistBadge(section=None, **kwargs):
            cache = page.__dict__.setdefault('_test_checklist', {})
            if 'checklist' not in cache:
                computed.append(True)
                cache['checklist'] = dict(header='ok', speakers=None)
            return cache['checklist'][section]

        monkeypatch.setattr(self.tblobj, 'checklistBadge', checklistBadge, raising=False)
        monkeypatch.delitem(page.__dict__, '_test_checklist', raising=False)
        result = page.menu.getMenuLineBadges(badges=self._badges(
            dict(table=TABLE, handler='checklistBadge', section='header'),
            dict(table=TABLE, handler='checklistBadge', section='speakers'),
            dict(table=TABLE, handler='#:name')))
        assert result['r_0'] == 'ok'
        assert result['r_1'] is None
        assert result['r_2'] == 3
        assert len(computed) == 1

    def test_no_badges(self):
        assert not self.page.menu.getMenuLineBadges(badges=Bag())
        assert not self.page.menu.getMenuLineBadges()
