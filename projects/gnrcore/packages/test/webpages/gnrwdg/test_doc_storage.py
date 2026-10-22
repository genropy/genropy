"""Docs as Markdown in the documentation storage, written in place.

Log in to the instance: sys/ep_doc never answers a guest. A user with the tag
_DOC_ (or doc_<package>) is a documenter: in documentation mode the ⓘ of an
empty doc shows red, a click opens the editor, Save writes
documentation:<pkg>/<table>/... and from then on everybody sees the ⓘ. Without
a configured documentation service the docs are files of the site folder.

  test_1_fields  fields of adm.user: each documents its column
                 (field:adm.user:<column>), the same doc in every form
  test_2_cards   a card and a Bag-backed grid of the card_profile resource:
                 one doc (grouplet:test:card_profile) filled with each row's
                 values; the editor offers the row's fields as variables
  test_3_page    a widget with helpcode outside a table documents the page
                 (page:test/<page>:delivery)
"""
from gnr.core.gnrbag import Bag


class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                     gnrcomponents/grouplet/grouplet:GroupletCardHandler,
                     gnrcomponents/grouplet/grouplet:GroupletGridHandler"""

    def test_0_mode(self, pane):
        """Documentation mode: a documenter sees the empty docs, red"""
        pane.checkbox(value='^gnr.docModeVisible', label='!!Documentation mode')

    def test_1_fields(self, pane):
        """Each field documents its column"""
        fb = pane.formlet(cols=2, table='adm.user', datapath='.user')
        fb.field('username')
        fb.field('email')
        fb.field('firstname')
        fb.field('lastname')

    def test_2_cards(self, pane):
        """A card and a grid of the same resource share its doc"""
        pane.data('.shipping', Bag(dict(street='Via Roma 1', city='Milano', province='MI')))
        pane.groupletCard(datapath='.shipping', resource='card_profile', width='22em', margin_bottom='12px')
        rows = Bag()
        for i, (city, province) in enumerate((('Milano', 'MI'), ('Torino', 'TO'), ('Bari', 'BA'))):
            rows.setItem('r_%s' % i, Bag(dict(street='Via Roma %s' % (i + 1), city=city,
                                              province=province)))
        pane.data('.rows', rows)
        pane.groupletGrid(storepath='.rows', resource='card_profile', chromeSide='top',
                          cols=3, min_width='16em', nodeId='doc_rows')

    def test_3_page(self, pane):
        """A helpcode outside a table documents the page"""
        fb = pane.formlet(cols=2, datapath='.order')
        fb.textbox(value='^.delivery', lbl='!!Delivery notes', helpcode='delivery')
        fb.textbox(value='^.reference', lbl='!!Reference')
