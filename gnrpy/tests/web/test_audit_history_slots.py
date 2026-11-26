"""An explicitly configured history slot builds the audit history only for the history tags.

A toolbar listing ``tableAudit`` or ``form_audit`` reaches the slot handlers
of th_view/th_form directly, outside the default slots filtered by tag: the
check has to live in the palettes they build, or the event list of
``audit.event`` is loaded for any user.

Built for real on a GnrDummySite over a postgres instance with the audit
package and table audit_test.audited_item (audit='external') of the
test_invoice project; postgres because the audit package is postgres only.
"""

import inspect
import os

from core.common import BaseGnrTest
from sql.common import get_pg_config

from gnr.app.gnrapp import GnrApp
from gnr.core.gnrbag import Bag
from gnr.dev.makers.instance import InstanceMaker
from gnr.web.gnrdummysite import GnrDummySite
from gnr.web.gnrwebstruct import GnrDomSrc_dojo_11

INSTANCE = 'audit_history_slots'
PACKAGES = ('gnrcore:sys', 'gnrcore:adm', 'gnrcore:audit', 'test_invoice:audit_test')
SLOTS = 'tableAudit,form_audit'


def struct_nodes(struct):
    for node in struct.nodes:
        yield node
        if isinstance(node.value, Bag):
            yield from struct_nodes(node.value)


class TestAuditHistorySlots(BaseGnrTest):

    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.pg_instance = None
        cls.app = None
        try:
            cls._build_site()
        except BaseException:
            cls.teardown_class()
            raise

    @classmethod
    def _build_site(cls):
        pg_conf, cls.pg_instance = get_pg_config()
        pg_conf.pop('database', None)
        cls.dbname = '%s_%s' % (INSTANCE, os.getpid())
        base_path = os.path.join(cls.tmp_conf_dir, INSTANCE, 'instances')
        InstanceMaker(INSTANCE, base_path=base_path).do()
        config_path = os.path.join(base_path, INSTANCE, 'config', 'instanceconfig.xml')
        config = Bag(config_path)
        config.setItem('db', None, implementation='postgres', dbname=cls.dbname, **pg_conf)
        config.setItem('packages', None)
        for pkg in PACKAGES:
            config.setItem('packages.%s' % pkg.replace(':', '_'), None, pkgcode=pkg)
        config.toXml(config_path, typevalue=False, pretty=True)
        cls.app = GnrApp(INSTANCE)
        cls.app.db.model.check(applyChanges=True)
        cls.app.db.commit()
        cls.site = GnrDummySite(INSTANCE, site_name=INSTANCE)

    @classmethod
    def teardown_class(cls):
        try:
            if getattr(cls, 'app', None) is not None:
                site = getattr(cls, 'site', None)
                if site is not None:
                    site.db.closeConnection()
                cls.app.db.closeConnection()
                cls.app.db.dropDb(cls.dbname)
        finally:
            if getattr(cls, 'pg_instance', None) is not None:
                cls.pg_instance.stop()
            super().teardown_class()

    def build_slots(self, tags):
        page = self.site.dummyPage
        page.avatar = self.site.gnrapp.makeAvatar(user='slot_tester', user_id='slot_tester',
                                                  tags=tags, group_code=None)
        page.mixinComponent('th/th:TableHandler')
        root = GnrDomSrc_dojo_11.makeRoot(page)
        page._root = root
        previous_page = self.site.currentPage
        # the grid struct reads the saved views of the user asking for it
        self.site.currentPage = page
        try:
            frame = root.framePane(frameCode='items', table='audit_test.audited_item', th_root='items')
            frame.top.slotToolbar(SLOTS)
        finally:
            self.site.currentPage = previous_page
        return page, list(struct_nodes(root))

    def test_component_under_test(self):
        page, nodes = self.build_slots('user,auditHistory')
        component_file = inspect.getsourcefile(page.audit_tableHistoryPalette)
        assert component_file == os.path.join(self.test_genro_root, 'projects', 'gnrcore', 'packages',
                                              'audit', 'resources', 'audit_components.py')

    def test_the_history_tags_build_the_palettes(self):
        page, nodes = self.build_slots('user,auditHistory')
        palettes = [node.attr['paletteCode'] for node in nodes if node.attr.get('tag') == 'PalettePane']
        assert 'items_tableHistory' in palettes
        assert 'items_recordHistory' in palettes
        event_grids = [node.attr['nodeId'] for node in nodes
                       if node.attr.get('tag') == 'NewIncludedView' and node.attr.get('table') == 'audit.event']
        assert 'V_items_tableHistory_th_grid' in event_grids
        stores = [node.attr['nodeId'] for node in nodes
                  if node.attr.get('tag') == 'SelectionStore' and node.attr.get('table') == 'audit.event']
        assert 'V_items_tableHistory_th_grid_store' in stores
        record_grids = [node.attr.get('nodeId') for node in nodes
                        if node.attr.get('frameCode') == 'items_recordHistory_events'
                        and str(node.attr.get('tag')).lower() == 'newincludedview']
        assert record_grids == ['items_recordHistory_events_grid']

    def test_without_the_history_tags_nothing_is_built(self):
        page, nodes = self.build_slots('user,admin,superadmin')
        assert [(node.label, node.attr.get('tag')) for node in nodes] == [
            ('FramePane_0', 'FramePane'), ('top', 'autoslot'), ('bar', 'slotBar'),
            ('tableAudit', 'slot'), ('form_audit', 'slot')]
