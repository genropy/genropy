"""The published manual in the "?" of the page (gnr.web.gnrmanual, sys/ep_doc).

The manual is a Sphinx + myst-parser site, test/docs/manual: each section carries
the label of the element it documents, e.g. (help-field-adm-user-email)= for
the email field of adm.user. The manuals a user reaches are the adm.helpdoc of
the user's group, then those linked to no group. Log in, then:

  test_0_manual  builds the demo manual into the site folder and links it as an
                 adm.helpdoc of no group (Sphinx and myst-parser must be installed)
  test_1_fields  username and email have a section: their "?" opens it in the
                 help panel on the right, with "Open in the manual"; firstname
                 has none, so no "?"
  test_2_card    the card_profile grouplet: its ⓘ opens the card's section
  test_3_block   a roundedGroup with helpcode: the section of the page's part
  test_4_view    a table handler view of adm.user: the "?" of its toolbar opens
                 the section of the table
This page sets doc_editor_tags='user': in documentation mode any logged user
adds a customer's note under the manual's section.
"""
import os

from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method
from gnr.web import gnrmanual

try:
    from sphinx.cmd.build import build_main
except ImportError:
    build_main = None


class GnrCustomWebPage(object):
    doc_editor_tags = 'user'
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                     gnrcomponents/grouplet/grouplet:GroupletCardHandler,
                     th/th:TableHandler"""

    def test_0_manual(self, pane):
        """Build the demo manual and link it to everybody"""
        bar = pane.div(display='flex', gap='12px', align_items='center')
        bar.button('!!Build and link the demo manual', action='FIRE .build;')
        bar.checkbox(value='^gnr.docModeVisible', label='!!Documentation mode')
        pane.div('^.result', margin_top='6px')
        pane.dataRpc('.result', self.buildDemoManual, _fired='^.build', _lockScreen=True)

    @public_method
    def buildDemoManual(self):
        if build_main is None:
            return 'Sphinx is not installed: pip install sphinx myst-parser'
        source = os.path.join(self.site.gnrapp.packages['test'].packageFolder, 'docs', 'manual')
        build = self.site.storageNode('site:_demo_manual', autocreate=True)
        if build_main(['-q', '-b', 'html', source, build.internal_path]):
            return 'The demo manual did not build'
        url = 'site:_demo_manual/users.html'
        with self.db.table('adm.helpdoc').recordToUpdate(title='Demo manual', insertMissing=True) as rec:
            rec['title'] = 'Demo manual'
            rec['url'] = url
        self.db.commit()
        gnrmanual._cache.clear()
        return f'Built and linked to everybody as {url}. Reload the page.'

    def test_1_fields(self, pane):
        """Fields of adm.user: the "?" of a documented column"""
        fb = pane.formlet(cols=3, table='adm.user', datapath='.user')
        fb.field('username')
        fb.field('email')
        fb.field('firstname')

    def test_2_card(self, pane):
        """A grouplet card and its section"""
        pane.data('.shipping', Bag(dict(street='Via Roma 1', city='Milano', province='MI')))
        pane.groupletCard(datapath='.shipping', resource='card_profile', width='22em')

    def test_3_block(self, pane):
        """A roundedGroup with helpcode: a part of the page"""
        box = pane.div(height='120px', position='relative')
        content = box.roundedGroup(title='!!Shipping', helpcode='shipping', height='100%')
        content.div('A block of the page with its own "?".', padding='8px')

    def test_4_view(self, pane):
        """A table handler view: the "?" of the table in its toolbar"""
        pane.borderContainer(height='260px').contentPane(region='center').plainTableHandler(
            table='adm.user', viewResource='View')
