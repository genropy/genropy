from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Guest', priority=2)

    def grouplet_main(self, pane, num_guests=None, **kwargs):
        num_guests = int(num_guests or 1)
        tc = pane.tabContainer(tabPosition='left-h')
        main_tab = tc.contentPane(title='Main Guest', padding='10px')
        fb = main_tab.formlet(cols=2, table='test.booking')
        fb.field('guest_name', lbl='Guest Name', colspan=2, width='100%',
                 validate_notnull=True)
        fb.field('guest_email', lbl='Email', validate_notnull=True)
        fb.field('guest_phone', lbl='Phone')
        fb.field('document_type', tag='filteringSelect',
                 values='id_card:ID Card,passport:Passport,driving_license:Driving License',
                 lbl='Document Type')
        fb.field('document_number', lbl='Document Number')
        for i in range(num_guests - 1):
            guest_path = f'.other_guests.guest_{i}'
            tab = tc.contentPane(title=f'Guest {i + 2}',
                                 datapath=guest_path,
                                 padding='10px')
            fb = tab.formlet(cols=2)
            fb.textbox(value='^.name', lbl='Name',
                       colspan=2, width='100%')
            fb.filteringSelect(
                value='^.document_type',
                values='id_card:ID Card,passport:Passport,driving_license:Driving License',
                lbl='Document Type')
            fb.textbox(value='^.document_number',
                       lbl='Document Number')
