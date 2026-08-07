# -*- coding: utf-8 -*-
"""Coverage for the template-driven printing path of BagToHtmlWeb.

The generic ``tables/_default/html_res/print_record_template`` resource relies on
``record_template`` being resolved by ``contentFromTemplate``; these tests pin
that behaviour and the silent fallback that hits callers who pass a template
*name* where a compiled Bag is expected.
"""

import os
import tempfile

import pytest

from gnr.app.gnrapp import GnrApp
from gnr.core.gnrbag import Bag
from gnr.core.gnrlang import gnrImport
from gnr.web.gnrbaseclasses import TableTemplateToHtml

REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

CUSTOMER_TPL = os.path.join(REPO_ROOT, 'projects', 'test_invoice', 'packages', 'invc',
                            'resources', 'tables', 'customer', 'tpl', 'default.xml')

DEFAULT_RESOURCE = os.path.join(REPO_ROOT, 'resources', 'common', 'tables', '_default',
                                'html_res', 'print_record_template.py')

ACCOUNT_NAME = 'Template Regression SpA'


class StubPage(object):
    """Minimal page: records the addresses asked for, returns a real compiled Bag."""

    def __init__(self, compiled):
        self._compiled = compiled
        self.loaded = []

    def loadTemplate(self, template_address, **kwargs):
        self.loaded.append(template_address)
        return self._compiled


class StubSite(object):
    def externalUrl(self, url, **kwargs):
        return url


@pytest.fixture(scope='module')
def customer_table():
    """A real sqlite test_invoice db with one customer record."""
    tmpdir = tempfile.mkdtemp()
    app = GnrApp('test_invoice', db_attrs=dict(
        implementation='sqlite',
        dbname=os.path.join(tmpdir, 'testing'),
    ))
    app.db.model.check(applyChanges=True)
    tbl = app.db.table('invc.customer')
    record = tbl.newrecord(account_name=ACCOUNT_NAME, street_address='Via Regression 1')
    tbl.insert(record)
    app.db.commit()
    return tbl, record[tbl.pkey]


@pytest.fixture(scope='module')
def compiled_template():
    """The compiled Bag of the invc.customer 'default' template resource."""
    return Bag(CUSTOMER_TPL)['compiled']


def _builder(table, page, site=None):
    """A TableTemplateToHtml wired with just what contentFromTemplate touches.

    BagToHtmlWeb.__init__ pulls in the pdf service, the htmltemplate loader and
    the letterhead machinery, none of which take part in template rendering.
    """
    builder = TableTemplateToHtml.__new__(TableTemplateToHtml)
    builder.page = page
    builder.tblobj = table
    builder.db = table.db
    builder.site = site or StubSite()
    builder.record_template = None
    builder.record = None
    return builder


def test_record_template_is_resolved_against_own_table(customer_table, compiled_template):
    """record_template alone must drive loadTemplate and render real field values."""
    table, pkey = customer_table
    page = StubPage(compiled_template)
    builder = _builder(table, page)
    builder.record_template = 'default'

    html = builder.contentFromTemplate(pkey)

    assert page.loaded == ['invc.customer:default']
    assert ACCOUNT_NAME in html
    assert 'Via Regression 1' in html


def test_explicit_template_bag_wins_over_record_template(customer_table, compiled_template):
    """An explicit compiled Bag must skip the loadTemplate lookup entirely."""
    table, pkey = customer_table
    page = StubPage(compiled_template)
    builder = _builder(table, page)
    builder.record_template = 'default'

    html = builder.contentFromTemplate(pkey, template=compiled_template)

    assert page.loaded == []
    assert ACCOUNT_NAME in html


def test_template_name_string_is_echoed_not_resolved(customer_table, compiled_template):
    """Regression: a template *name* is not a template.

    contentFromTemplate only special-cases Bag; any other value goes to
    templateReplace, which returns a string containing no '$' unchanged. The
    caller gets a document whose whole body is the name they passed.
    """
    table, pkey = customer_table
    page = StubPage(compiled_template)
    builder = _builder(table, page)

    result = builder.contentFromTemplate(pkey, template='stampa_badge')

    assert result == 'stampa_badge'
    assert ACCOUNT_NAME not in result
    assert page.loaded == []


def test_default_html_res_resource_prints_a_record_template():
    """The generic _default resource must be a TableTemplateToHtml subclass."""
    assert os.path.isfile(DEFAULT_RESOURCE)
    module = gnrImport(DEFAULT_RESOURCE, avoidDup=True)
    assert issubclass(module.Main, TableTemplateToHtml)
