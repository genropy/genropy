"""Tests for the selection-aware export of docu.handbook.

The export_to_sphinx batch runs on the handbooks the framework hands it: the
gear menu of the view delivers the current grid selection, the form toolbar
button delivers the pkey of the record on screen as an extra parameter. Both end
up in the same loop, which sets up the state of one handbook at a time, runs the
export steps on it and publishes it before moving to the next, so a manual that
fails costs only its own export.

The sphinx build is the one thing these tests replace, with steps writing a file
of their own: everything around it - the selection resolved through
BaseResourceBatch, the thermo bookkeeping of the framework, the publishing into
the real handbook storages and the record updates - is the real code, running on
a real database.
"""
import os
import shutil
import tempfile
from datetime import datetime

import pytest

from gnr.core.gnrlang import gnrImport
from gnr.web.gnrwebpage_proxy.serverbatch import GnrWebBatch

from core.common import BaseGnrAppTest
from sitestub import StorageSiteStub


class BatchProxyStub(GnrWebBatch):
    """The real thermo bookkeeping of the batch proxy, minus the user store.

    thermo_wrapper and the line accounting the loop relies on are inherited
    untouched; only the datachanges they publish, which need a live page store,
    are replaced by an in-memory log the tests can read.
    """

    def __init__(self, page):
        self.page = page
        self.line_codes = []
        self.cancellable = False
        self.delay = 0
        self.last_ts = datetime.now()
        self.messages = []
        self.logged = []

    def thermo_line_add(self, code, maximum=None, message=None, thermo_class=None):
        self.line_codes.append(code)

    def thermo_line_del(self, code):
        self.line_codes.remove(code)

    def thermo_line_update(self, code, progress=None, message=None, maximum=None):
        if code in self.line_codes:
            self.messages.append((code, message))

    def log_write(self, logtxt):
        self.logged.append(logtxt)


class PortableDocTable:
    """The documentation table, with the page tree read without its filter.

    Everything is delegated to the real table but getHierarchicalData, whose
    is_published condition is written in PostgreSQL (ILIKE over an EXISTS
    subquery) and is rejected by the sqlite database these tests run on.
    """

    def __init__(self, doctable):
        self.doctable = doctable

    def __getattr__(self, name):
        return getattr(self.doctable, name)

    def getHierarchicalData(self, condition=None, **kwargs):
        return self.doctable.getHierarchicalData(**kwargs)


class TestExportToSphinxSelection(BaseGnrAppTest):

    @classmethod
    def setup_class(cls):
        super().setup_class()
        cls.db = cls.app.db
        cls.db.model.check(applyChanges=True)
        cls.tbl = cls.db.table('docu.handbook')
        cls.doctbl = cls.db.table('docu.documentation')
        cls.dirs = {name: tempfile.mkdtemp(prefix='gnr_docu_%s_' % name)
                    for name in ('handbooks', 'local_handbooks', 'page')}
        cls.app.site = StorageSiteStub(cls.app, 'docu', cls.dirs)
        cls._makeFixture()

    @classmethod
    def teardown_class(cls):
        for folder in getattr(cls, 'dirs', {}).values():
            shutil.rmtree(folder, ignore_errors=True)
        super().teardown_class()

    @classmethod
    def _makeFixture(cls):
        docroot = dict(name='selroot')
        cls.doctbl.insert(docroot)
        cls.docroot_id = docroot['id']
        cls.ids = {name: cls._addHandbook(name, **kwargs) for name, kwargs in (
            ('alpha', {}), ('beta', {}), ('gamma', {}),
            ('zipped', dict(is_local_handbook=True)))}
        cls.db.commit()

    @classmethod
    def _addHandbook(cls, name, **kwargs):
        record = dict(name=name, title=name.capitalize(), language='en',
                      docroot_id=cls.docroot_id, **kwargs)
        cls.tbl.insert(record)
        return record['id']

    # ------------------------------------------------------------------
    # batch wiring
    # ------------------------------------------------------------------

    def _module(self):
        pytest.importorskip('sphinx')
        pytest.importorskip('boto3')
        module_path = os.path.join(self.app.packages['docu'].packageFolder,
                                   'resources', 'tables', 'handbook', 'action',
                                   'export_to_sphinx.py')
        return gnrImport(module_path, avoidDup=True)

    def _batch(self, broken=None, broken_setup=None, exploding=None, **kwargs):
        """Export batch whose sphinx build is replaced by two steps writing a
        recognizable build folder, so the loop around them runs for real.

        :param broken: names of the handbooks whose build must fail
        :param broken_setup: names of the handbooks whose setup must fail, where
                             the reachable failures of a real export are (an
                             unpublished tree, the handbook storage node, a pkey
                             that no longer resolves)
        :param exploding: exception class the broken handbooks raise
        """
        module = self._module()
        broken = broken or []
        broken_setup = broken_setup or []
        exploding = exploding or RuntimeError

        class SelectionExport(module.Main):
            batch_steps = 'writeSource,fakeSphinxBuild'

            def prepareHandbook(self, handbook_id):
                name = self.tblobj.readColumns(columns='$name', pkey=handbook_id)
                if name in broken_setup:
                    raise exploding('the setup of %s failed' % name)
                super().prepareHandbook(handbook_id)

            def step_writeSource(self):
                "Write source"
                with self.sourceDirNode.child('index.rst').open('wb') as rst_file:
                    rst_file.write(self.handbook_record['name'].encode())

            def step_fakeSphinxBuild(self):
                "Build HTML docs"
                self.resultNode = self.sphinxNode.child('build')
                with self.resultNode.child('index.html').open('wb') as html_file:
                    html_file.write(b'<html>%s</html>' % self.handbook_record['name'].encode())
                if self.handbook_record['name'] in broken:
                    raise exploding('the build of %s failed' % self.handbook_record['name'])

        page = self.app.site.currentPage
        page.btc = BatchProxyStub(page)
        return SelectionExport(page=page, resource_table=self.tbl, **kwargs)

    def _run(self, batch, **parameters):
        batch.batch_parameters = parameters
        batch.pre_process()
        batch.doctable = PortableDocTable(batch.doctable)
        batch.call_steps()
        return batch

    def _record(self, name):
        return self.tbl.record(self.ids[name]).output('dict')

    def _published(self, name):
        return self.app.site.storageNode('handbooks:%s/index.html' % name)

    # ------------------------------------------------------------------
    # which handbooks the run exports
    # ------------------------------------------------------------------

    def test_selection_drives_the_export(self):
        """The gear menu of the view hands the batch the grid selection: the run
        exports every handbook of it, which is what the entry was missing."""
        batch = self._batch()
        batch.selectedPkeys = [self.ids['alpha'], self.ids['beta']]
        batch.pre_process()
        assert batch.handbookIds() == batch.handbook_ids
        assert set(batch.handbook_ids) == {self.ids['alpha'], self.ids['beta']}

    def test_form_button_parameter_is_the_fallback(self):
        """The form toolbar button passes the record on screen as handbook_id and
        no selection at all: it keeps exporting exactly that handbook."""
        batch = self._batch()
        batch.batch_parameters = dict(extra_parameters=dict(handbook_id=self.ids['gamma']))
        assert batch.handbookIds() == [self.ids['gamma']]

    def test_selection_wins_over_the_extra_parameter(self):
        batch = self._batch()
        batch.selectedPkeys = [self.ids['alpha']]
        batch.batch_parameters = dict(extra_parameters=dict(handbook_id=self.ids['gamma']))
        assert batch.handbookIds() == [self.ids['alpha']]

    def test_no_selection_and_no_parameter_is_an_empty_run(self):
        """Neither entry point provided a handbook: the batch reports it instead
        of dying on the missing extra_parameters key."""
        batch = self._run(self._batch())
        assert batch.handbook_ids == []
        assert batch.result_handler() == ('No handbook to export', {})

    # ------------------------------------------------------------------
    # the loop
    # ------------------------------------------------------------------

    def test_every_handbook_of_the_selection_is_published(self):
        batch = self._batch()
        batch.selectedPkeys = [self.ids['alpha'], self.ids['beta'], self.ids['gamma']]
        self._run(batch)
        for name in ('alpha', 'beta', 'gamma'):
            assert self._published(name).exists
            record = self._record(name)
            assert record['last_exp_ts']
            assert record['handbook_url'].endswith('/%s/' % name)
        assert batch.result_handler()[0] == 'Export done'

    def test_each_handbook_builds_its_own_state(self):
        """Every step reads the handbook it is building from the batch: the state
        of the former export must not survive into the next one."""
        batch = self._batch()
        batch.selectedPkeys = [self.ids['alpha'], self.ids['beta']]
        self._run(batch)
        assert batch.handbook_record['name'] == 'beta'
        assert batch.publishedDocNode.fullpath == 'handbooks:beta'
        for name in ('alpha', 'beta'):
            with self._published(name).open('rb') as html_file:
                assert html_file.read() == b'<html>%s</html>' % name.encode()

    def test_the_thermo_names_the_handbook_being_exported(self):
        batch = self._batch()
        batch.selectedPkeys = [self.ids['alpha'], self.ids['beta']]
        self._run(batch)
        handbook_messages = [m for code, m in batch.page.btc.messages
                             if code == 'btc_handbooks']
        assert handbook_messages == ['alpha (1/2)', 'beta (2/2)']

    def test_the_step_thermo_survives_every_step(self):
        """The loop adds a thermo line above the steps, so the bookkeeping of the
        base call_steps has to start one line further down: the step line must
        still be there when the run ends."""
        batch = self._batch()
        batch.selectedPkeys = [self.ids['alpha'], self.ids['beta']]
        self._run(batch)
        btc = batch.page.btc
        assert btc.line_codes == ['btc_handbooks', 'btc_steps']
        step_messages = [m for code, m in btc.messages if code == 'btc_steps']
        assert step_messages == ['Write source', 'Build HTML docs'] * 2

    def test_a_local_handbook_is_published_as_a_zip(self):
        batch = self._batch()
        batch.selectedPkeys = [self.ids['zipped']]
        self._run(batch)
        zip_node = self.app.site.storageNode('local_handbooks:zipped/zipped.zip')
        assert zip_node.exists
        assert self._record('zipped')['local_handbook_zip'] == batch.zip_urls[0]
        assert batch.result_handler()[1] == dict(url=batch.zip_urls[0])

    def test_a_lone_zip_is_the_only_result_download(self):
        """Several zips have no single url to offer, so the batch result carries
        one only when the run produced exactly one."""
        batch = self._batch()
        batch.selectedPkeys = [self.ids['zipped'], self.ids['alpha']]
        self._run(batch)
        assert len(batch.zip_urls) == 1
        assert batch.result_handler()[1] == dict(url=batch.zip_urls[0])

    # ------------------------------------------------------------------
    # one failure does not end the run
    # ------------------------------------------------------------------

    def test_a_failing_handbook_does_not_abort_the_others(self):
        batch = self._batch(broken=['beta'])
        batch.selectedPkeys = [self.ids['alpha'], self.ids['beta'], self.ids['gamma']]
        self._run(batch)
        assert batch.failures == ['beta']
        assert self._published('alpha').exists
        assert self._published('gamma').exists
        assert not self._published('beta').exists
        assert self._record('gamma')['last_exp_ts']

    def test_the_failures_are_reported_in_the_result(self):
        batch = self._batch(broken=['beta'])
        batch.selectedPkeys = [self.ids['alpha'], self.ids['beta'], self.ids['gamma']]
        self._run(batch)
        assert batch.result_handler()[0] == 'Exported 2 of 3 handbooks, failed: beta'
        assert any('beta: export failed' in line for line in batch.page.btc.logged)

    def test_a_failing_handbook_is_not_registered_as_exported(self):
        """The record of a handbook whose build failed keeps the timestamp of its
        last good export: nothing of the failed run reaches the database."""
        previous = self._record('beta')['last_exp_ts']
        batch = self._batch(broken=['beta'])
        batch.selectedPkeys = [self.ids['beta']]
        self._run(batch)
        assert self._record('beta')['last_exp_ts'] == previous

    def test_a_handbook_failing_its_setup_does_not_abort_the_others(self):
        """The setup of a handbook is where the reachable failures are - a tree
        with nothing published, the handbook storage node it erases before the
        build, a pkey gone missing - so it has to be contained exactly like a
        failing build."""
        exported = {name: self._record(name)['last_exp_ts']
                    for name in ('alpha', 'beta', 'gamma')}
        batch = self._batch(broken_setup=['beta'])
        batch.selectedPkeys = [self.ids['alpha'], self.ids['beta'], self.ids['gamma']]
        self._run(batch)
        assert batch.failures == ['beta']
        assert self._record('alpha')['last_exp_ts'] != exported['alpha']
        assert self._record('gamma')['last_exp_ts'] != exported['gamma']
        assert self._record('beta')['last_exp_ts'] == exported['beta']
        assert batch.result_handler()[0] == 'Exported 2 of 3 handbooks, failed: beta'

    def test_the_first_handbook_failing_its_setup_is_reported_by_name(self):
        """A setup failing on the first handbook leaves the export with no state
        at all: the failure is named from the pkey the loop is iterating on, not
        from a record that was never loaded."""
        exported = self._record('gamma')['last_exp_ts']
        batch = self._batch(broken_setup=['beta'])
        batch.selectedPkeys = [self.ids['beta'], self.ids['gamma']]
        self._run(batch)
        assert batch.failures == ['beta']
        assert any('beta: export failed' in line for line in batch.page.btc.logged)
        assert self._record('gamma')['last_exp_ts'] != exported

    def test_the_user_stopping_the_batch_stops_the_run(self):
        """A failing handbook is skipped, but the user asking to stop is not a
        failure of a handbook: it has to reach the batch runner."""
        batch = self._batch(broken=['alpha'], exploding=GnrWebBatch.exception_stopped)
        batch.selectedPkeys = [self.ids['alpha'], self.ids['beta']]
        batch.batch_parameters = {}
        batch.pre_process()
        batch.doctable = PortableDocTable(batch.doctable)
        with pytest.raises(GnrWebBatch.exception_stopped):
            batch.call_steps()
        assert batch.failures == []
        assert not self._published('beta').exists
