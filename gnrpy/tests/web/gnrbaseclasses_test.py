"""Template-driven printing of one record: TableTemplateToHtml and the generic
``tables/_default/html_res/print_recordtemplate`` resource.

Everything runs on a real GnrDummySite over the isolated ``gnrtest`` instance,
with a real ``adm.user`` record and the real ``homepage`` template resource of
``adm.user``. The only stub is ``page.loadTemplate``: on sqlite its
``adm.userobject`` lookup emits Postgres-only SQL (#1165), so the stub skips
straight to ``templateFromResource``, the resource half of the same method.
"""

import os

from core.common import BaseGnrTest

from gnr.app.gnrapp import GnrApp
from gnr.web import gnrbaseclasses
from gnr.web.gnrbaseclasses import TableTemplateToHtml
from gnr.web.gnrdummysite import GnrDummySite

RESPATH = 'html_res/print_recordtemplate'
RESOURCE_MODULE = os.path.join('resources', 'common', 'tables', '_default',
                               'html_res', 'print_recordtemplate.py')
USERNAME = 'template_regression'


class TestTemplatePrinting(BaseGnrTest):

    @classmethod
    def setup_class(cls):
        super().setup_class()
        app = GnrApp(cls.test_instance_name)
        app.db.model.check(applyChanges=True)
        app.db.commit()
        cls.site = GnrDummySite(cls.test_instance_name, site_name=cls.test_instance_name)
        cls.table = cls.site.db.table('adm.user')
        record = cls.table.newrecord(username=USERNAME, firstname='Template',
                                     lastname='Regression', email='template@example.com')
        cls.table.insert(record)
        cls.site.db.commit()
        cls.pkey = record[cls.table.pkey]
        cls.compiled = cls.page().templateFromResource(table='adm.user',
                                                       tplname='homepage')[0]['compiled']

    @classmethod
    def page(cls):
        """A real headless page recording the template addresses it is asked for."""
        page = cls.site.dummyPage
        page.loaded = []

        def loadTemplate(template_address, **kwargs):
            page.loaded.append(template_address)
            table, tplname = template_address.split(':')
            return page.templateFromResource(table=table, tplname=tplname)[0]['compiled']
        page.loadTemplate = loadTemplate
        return page

    def test_module_under_test(self):
        # the editable install resolves gnr.* to the main checkout, so make sure
        # the module being exercised is the one in this working tree
        checkout = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        assert gnrbaseclasses.__file__.startswith(checkout + os.sep)

    def test_constructor_record_template_is_resolved_against_own_table(self):
        page = self.page()
        builder = TableTemplateToHtml(page=page, table=self.table, record_template='homepage')

        html = builder.contentFromTemplate(self.pkey)

        assert page.loaded == ['adm.user:homepage']
        assert USERNAME in html

    def test_explicit_template_bag_wins_over_record_template(self):
        page = self.page()
        builder = TableTemplateToHtml(page=page, table=self.table, record_template='homepage')

        html = builder.contentFromTemplate(self.pkey, template=self.compiled)

        assert page.loaded == []
        assert USERNAME in html

    def test_template_name_string_is_echoed_not_resolved(self):
        """Documents the trap tracked by #1166, not desired behaviour.

        contentFromTemplate only special-cases Bag; any other value goes to
        templateReplace, which returns a string containing no '$' unchanged, so
        the caller gets a document whose whole body is the name they passed.
        When contentFromTemplate learns to raise on a bare name, this test
        must be inverted, not deleted.
        """
        page = self.page()
        builder = TableTemplateToHtml(page=page, table=self.table)

        result = builder.contentFromTemplate(self.pkey, template='stampa_badge')

        assert result == 'stampa_badge'
        assert USERNAME not in result
        assert page.loaded == []

    def test_default_respath_resolves_through_the_tables_default_fallback(self):
        page = self.page()

        script = page.loadTableScript(table='adm.user', respath=RESPATH, record_template='homepage')

        assert isinstance(script, TableTemplateToHtml)
        assert script.tblobj is self.table
        module = __import__(type(script).__module__, fromlist=['Main'])
        assert module.__file__.endswith(os.sep + RESOURCE_MODULE)

    def test_default_respath_prints_a_record_through_named_template(self):
        page = self.page()
        script = page.loadTableScript(table='adm.user', respath=RESPATH, record_template='homepage')

        html = script(record=self.pkey)

        assert page.loaded == ['adm.user:homepage']
        assert USERNAME in html

    def test_default_respath_writes_a_pdf(self):
        page = self.page()
        script = page.loadTableScript(table='adm.user', respath=RESPATH, record_template='homepage')

        pdfpath = script(record=self.pkey, pdf=True)
        try:
            assert pdfpath.endswith('.pdf')
            assert os.path.isfile(pdfpath)
            assert os.path.getsize(pdfpath) > 0
        finally:
            for path in (pdfpath, script.filepath):
                if path and os.path.isfile(path):
                    os.remove(path)

    def test_call_time_record_template_leaves_no_sticky_state(self):
        page = self.page()
        script = page.loadTableScript(table='adm.user', respath=RESPATH)

        html = script(record=self.pkey, record_template='homepage')

        assert page.loaded == ['adm.user:homepage']
        assert USERNAME in html
        assert script.record_template is None

    def test_page_callTableScript_forwards_record_template(self):
        page = self.page()

        html = page.callTableScript(table='adm.user', respath=RESPATH,
                                    record=self.pkey, record_template='homepage')

        assert page.loaded == ['adm.user:homepage']
        assert USERNAME in html

    def test_site_callTableScript_forwards_record_template(self):
        page = self.page()

        html = self.site.callTableScript(page=page, table='adm.user', respath=RESPATH,
                                         record=self.pkey, record_template='homepage')

        assert page.loaded == ['adm.user:homepage']
        assert USERNAME in html
