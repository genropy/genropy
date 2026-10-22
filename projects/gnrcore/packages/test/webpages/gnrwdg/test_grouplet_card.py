"""groupletCard: a grouplet bound to a datapath with its chrome band.

  test_0_plain        a titled group filled in place, as a roundedGroup;
                      not collapsible unless asked
  test_1_roundedgroup the same fields in a roundedGroup and in a card
  test_2_in_form      cards as the groups of a record form: fold the
                      Customer card with VAT empty and its band stays
                      tinted red; Save, the semaphore and the values of a
                      folded card work as usual
  test_3_sides        the band on top, left and right; folded, a side band
                      lays out in a row with the title
  test_4_bound_state  folded state and checkbox at paths of the page,
                      custom menu entries
  test_5_nested       cards inside cards: chevrons as in a tree
  test_6_profile      the same resource three times: its own card profile,
                      the profile given by the caller, the resource's
                      profile overridden by the caller
  test_7_doc          the ⓘ doc, read from the inlinedoc storage: the
                      resource's own address, and a card in place pointing to
                      one with doc= (doc_kw fills its variables); empty docs
                      show their ⓘ only in documentation mode
  test_8_clear        Clear empties only the card's fields; with
                      delitem='==!invoiced' it greys out once Invoiced is ticked
  test_9_use_form     useForm=True: the grouplet edits a copy in a form of its
                      own, written back as it is saved (the dump on the right
                      follows a second later); City is required: emptied, the
                      band turns red and nothing is written back. Inside the
                      record form, the card reloads with the record.
"""
from gnr.core.gnrbag import Bag
from gnr.core.gnrdecorator import public_method


class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                     gnrcomponents/formhandler:FormHandler,
                     gnrcomponents/grouplet/grouplet:GroupletCardHandler,
                     public:Public"""

    def test_0_plain(self, pane):
        """A titled group filled in place: no chevron, collapsible is False by default"""
        pane.data('.contact', Bag(dict(name='Alice', phone='02 1234')))
        row = pane.div(display='flex', gap='12px', align_items='start')
        card = row.groupletCard(datapath='.contact', title='!!Contact', width='22em')
        self.contact_fields(card)
        card = row.groupletCard(datapath='.contact', title='!!Contact, collapsible', width='22em',
                                collapsible=True)
        self.contact_fields(card)

    def test_1_roundedgroup(self, pane):
        """The same fields in a roundedGroup and in a groupletCard, side by side"""
        pane.data('.contact', Bag(dict(name='Alice', phone='02 1234')))
        row = pane.div(display='flex', gap='12px', align_items='start')
        box = row.div(width='22em', height='150px', position='relative')
        self.contact_fields(box.roundedGroup(title='!!Contact (roundedGroup)', height='100%',
                                             datapath='.contact'))
        self.contact_fields(row.groupletCard(datapath='.contact', title='!!Contact (groupletCard)',
                                             width='22em'))

    def test_2_in_form(self, pane):
        """Cards as the groups of a record form"""
        pane.data('.customer', Bag(dict(name='ACME', vat='',
                                        shipping=Bag(dict(street='Via Roma 1', city='Milano',
                                                          province='MI')))))
        form = pane.frameForm(frameCode='card_form', height='420px', datapath='.card_form',
                              border='1px solid silver')
        form.formStore(storeType='Item', handler='memory', locationpath='.#parent.customer')
        form.top.slotToolbar('*,semaphore,formcommands,5')
        box = form.center.contentPane(datapath='.record', padding='10px', overflow='auto')
        main = box.groupletCard(title='!!Customer', collapsible=True, margin_bottom='10px')
        fb = main.formlet(cols=2)
        fb.textbox(value='^.name', lbl='Name', validate_notnull=True)
        fb.textbox(value='^.vat', lbl='VAT', validate_notnull=True)
        box.groupletCard(datapath='.shipping', resource='card_profile')
        form.dataController('this.form.load()', _onStart=True)

    def test_3_sides(self, pane):
        """The band on top, left and right, open and folded"""
        pane.data('.contact', Bag(dict(name='Alice', phone='02 1234')))
        row = pane.div(display='flex', gap='12px', align_items='start', flex_wrap='wrap')
        for side in ('top', 'left', 'right'):
            for collapsible in (True, 'closed'):
                card = row.groupletCard(datapath='.contact', titleField='name', chromeSide=side,
                                        collapsible=collapsible, checkbox=f'^.checked_{side}',
                                        width='16em')
                self.contact_fields(card)

    def test_4_bound_state(self, pane):
        """Folded state and checkbox at paths of the page, custom menu entries"""
        pane.data('.contact', Bag(dict(name='Alice', phone='02 1234')))
        pane.data('.state', Bag(dict(collapsed=False, checked=True)))
        bar = pane.div(display='flex', gap='1em', align_items='center', margin_bottom='8px')
        bar.checkbox(value='^.state.collapsed', label='Folded')
        bar.checkbox(value='^.state.checked', label='Checked')
        bar.div('^.state.last_action', _class='test_note')
        card = pane.groupletCard(datapath='.contact', titleTemplate='$name ($phone)',
                                 collapsible=True, collapsed='^.state.collapsed',
                                 checkbox='^.state.checked', width='24em', nodeId='card_bound',
                                 editmenu=dict(call=dict(label='Call', iconClass='iconbox phone'),
                                               mail=dict(label='Write',
                                                         action="SET .state.last_action='write';")))
        self.contact_fields(card)
        pane.dataController("SET .state.last_action = $1.action;",
                            subscribe_groupletCard_card_bound_action=True)

    def test_5_nested(self, pane):
        """Cards inside cards: chevrons as in a tree"""
        pane.data('.budget', Bag(dict(name='Shooting', crew=Bag(dict(name='Crew', director='Bruno')),
                                      cast=Bag(dict(name='Cast', lead='Carla')))))
        chapter = pane.groupletCard(datapath='.budget', titleField='name', collapsible=True,
                                    width='30em')
        chapter.formlet(cols=1).textbox(value='^.name', lbl='Chapter')
        for key, field in (('crew', 'director'), ('cast', 'lead')):
            account = chapter.groupletCard(datapath=f'.{key}', titleTemplate=f'$name · ${field}',
                                           collapsible='closed', margin_top='8px')
            fb = account.formlet(cols=2)
            fb.textbox(value='^.name', lbl='Account')
            fb.textbox(value=f'^.{field}', lbl=field.capitalize())

    def test_6_profile(self, pane):
        """One resource three times: its own profile, the caller's, both"""
        pane.data('.shipping', Bag(dict(street='Via Roma 1', city='Milano', province='MI')))
        row = pane.div(display='flex', gap='12px', align_items='start', flex_wrap='wrap')
        row.groupletCard(datapath='.shipping', resource='card_profile', width='22em')
        row.groupletCard(datapath='.shipping', handler=self.shipping_fields, width='22em',
                         titleTemplate='$city', collapsible=True, tools='collapse,title,menu',
                         delitem=True)
        row.groupletCard(datapath='.shipping', resource='card_profile', width='22em',
                         chromeSide='left', collapsible='closed', tools='collapse,title',
                         titleTemplate='!!Ship to $street')

    def test_7_doc(self, pane):
        """The ⓘ doc of the resource and of a card in place, from the inlinedoc storage"""
        pane.data('.shipping', Bag(dict(street='Via Roma 1', city='Milano', province='MI')))
        pane.checkbox(value='^gnr.docModeVisible', label='!!Documentation mode')
        row = pane.div(display='flex', gap='12px', align_items='start')
        row.groupletCard(datapath='.shipping', handler=self.shipping_fields, width='22em',
                         title='!!Card in place', doc='grouplet:test:shipping_notes',
                         doc_kw=dict(when='every morning'))
        row.groupletCard(datapath='.shipping', resource='card_profile', width='22em')

    def test_8_clear(self, pane):
        """Clear empties only the card's fields, unless the row is invoiced"""
        pane.data('.order', Bag(dict(number='A-17',
                                     shipping=Bag(dict(street='Via Roma 1', city='Milano',
                                                       province='MI', invoiced=False)))))
        pane.checkbox(value='^.order.shipping.invoiced', label='Invoiced')
        pane.div('^.order.number', margin='6px 0')
        card = pane.groupletCard(datapath='.order.shipping', title='!!Shipping', width='24em',
                                 delitem='==!invoiced', collapsible=True)
        self.shipping_fields(card)

    def test_9_use_form(self, pane):
        """useForm=True: the grouplet in a form of its own, inside a record form and alone"""
        pane.data('.customer', Bag(dict(name='ACME', shipping=Bag(dict(street='Via Roma 1',
                                                                      city='Milano', province='MI')))))
        pane.data('.alone', Bag(dict(street='Corso Italia 9', city='Torino', province='TO')))
        row = pane.div(display='flex', gap='12px', align_items='start')
        form = row.frameForm(frameCode='card_useform', height='300px', width='34em',
                             datapath='.card_useform', border='1px solid silver')
        form.formStore(storeType='Item', handler='memory', locationpath='.#parent.customer')
        form.top.slotToolbar('*,semaphore,formcommands,5')
        box = form.center.contentPane(datapath='.record', padding='10px', overflow='auto')
        box.formlet(cols=1).textbox(value='^.name', lbl='Name')
        box.groupletCard(datapath='.shipping', handler=self.shipping_required, useForm=True,
                         titleTemplate='$city', collapsible=True, margin_top='8px')
        form.dataController('this.form.load()', _onStart=True)
        side = row.div(width='24em')
        side.groupletCard(datapath='.alone', handler=self.shipping_required, useForm=True,
                          title='!!Alone, useForm', delitem=True)
        dump = side.div(font_family='monospace', font_size='12px', margin_top='8px')
        dump.div('Stored at .alone')
        for field in ('street', 'city', 'province'):
            dump.div(f'^.alone.{field}')

    @public_method
    def shipping_required(self, pane, **kwargs):
        fb = pane.formlet(cols=2)
        fb.textbox(value='^.street', lbl='Street', colspan=2)
        fb.textbox(value='^.city', lbl='City', validate_notnull=True)
        fb.textbox(value='^.province', lbl='Province', width='4em')

    def contact_fields(self, pane):
        fb = pane.formlet(cols=1)
        fb.textbox(value='^.name', lbl='Name')
        fb.textbox(value='^.phone', lbl='Phone')

    @public_method
    def shipping_fields(self, pane, **kwargs):
        fb = pane.formlet(cols=2)
        fb.textbox(value='^.street', lbl='Street', colspan=2)
        fb.textbox(value='^.city', lbl='City')
        fb.textbox(value='^.province', lbl='Province', width='4em')
