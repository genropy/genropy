"""Real checks on ``tableBranch`` menu nodes (#1639).

The menu is resolved against the ``gnrtest`` instance: the branch lines come
from real ``adm.htmltemplate`` records, and the badges are computed by the real
``menu.getMenuLineBadge`` of the headless page.
"""

from core.common import BaseGnrTest

from gnr.app.gnrapp import GnrApp
from gnr.web.gnrdummysite import GnrDummySite
from gnr.web.gnrmenu import MenuResolver, MenuStruct

TABLE = 'adm.htmltemplate'
BRANCH_ID = 'tb1639'


class _FixedSourceResolver(MenuResolver):
    def __init__(self, struct, **kwargs):
        self._struct = struct
        super().__init__(**kwargs)

    @property
    def sourceBag(self):
        return self._struct


class TestTableBranch(BaseGnrTest):

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

    def _branch(self, **kwargs):
        struct = MenuStruct(page=self.page)
        struct.tableBranch('Days', table=TABLE, **kwargs)
        return _FixedSourceResolver(struct, _page=self.page, path=None).load().getNode('#0')

    def _lines(self, branch_node):
        return [n.attr for n in branch_node.getValue()]

    def test_handler_badge_on_table_branch(self):
        node = self._branch(menuLineBadge='#:name', badgeClass='days_badge',
                            webpage='/test/days')
        assert node.attr['badgeContent'] == 3
        assert node.attr['badgeClass'] == 'days_badge'

    def test_badge_kwargs_do_not_leak_onto_lines(self):
        node = self._branch(menuLineBadge='#:!name', menuLineBadge_table=TABLE,
                            badgeClass='days_badge', webpage='/test/days')
        assert node.attr['badgeContent'] == 1
        for attr in self._lines(node):
            assert not [k for k in attr if 'menuLineBadge' in k or k == 'badgeClass']

    def test_child_count_badge_unchanged(self):
        node = self._branch(menuLineBadge='#', webpage='/test/days')
        assert node.attr['child_count'] == 4
        assert node.attr['badgeContent'] == 4

    def test_line_hook_display_attributes_stay_on_node(self, monkeypatch):
        def dynamicMenuLine(record):
            past = record['name'] == 'day_1'
            return dict(customLabelClass='day_past' if past else None,
                        badgeContent='<span class="dot"></span>',
                        badgeClass='dot_badge', mode='view')
        monkeypatch.setattr(self.tblobj, f'menu_dynamicMenuLine_{BRANCH_ID}',
                            dynamicMenuLine, raising=False)
        node = self._branch(branchId=BRANCH_ID, webpage='/test/days',
                            query_where='$name IS NOT NULL', query_order_by='$name')
        lines = self._lines(node)
        assert len(lines) == 3
        for attr in lines:
            assert attr['badgeContent'] == '<span class="dot"></span>'
            assert attr['badgeClass'] == 'dot_badge'
            assert attr['url_mode'] == 'view'
            assert not [k for k in attr if k in ('url_customLabelClass', 'url_badgeContent',
                                                 'url_badgeClass')]
        assert 'day_past' in lines[0]['labelClass']
        assert 'day_past' not in lines[1]['labelClass']

    def test_line_hook_display_attributes_on_thpage_lines(self, monkeypatch):
        monkeypatch.setattr(self.tblobj, f'menu_dynamicMenuLine_{BRANCH_ID}',
                            lambda record: dict(customLabelClass='day_past', badgeContent='x'),
                            raising=False)
        node = self._branch(branchId=BRANCH_ID, query_where='$name IS NOT NULL')
        for attr in self._lines(node):
            assert attr['badgeContent'] == 'x'
            assert 'day_past' in attr['labelClass']

    def test_add_line_keeps_its_label_class(self):
        node = self._branch(webpage='/test/days', add_label='New day')
        add_line = self._lines(node)[-1]
        assert 'addTableItem' in add_line['labelClass']
        assert 'url_customLabelClass' not in add_line

    def test_refresh_on_tables_subscribes_extra_tables(self, monkeypatch):
        subscribed = []
        monkeypatch.setattr(self.page, 'subscribeTable',
                            lambda table, *args, **kwargs: subscribed.append(table))
        node = self._branch(webpage='/test/days',
                            refreshOnTables='adm.htmltemplate_atc, adm.user')
        assert set(subscribed) == {TABLE, 'adm.htmltemplate_atc', 'adm.user'}
        assert node.attr['refreshOnTables'] == 'adm.htmltemplate_atc, adm.user'
        for attr in self._lines(node):
            assert not [k for k in attr if 'refreshOnTables' in k]
