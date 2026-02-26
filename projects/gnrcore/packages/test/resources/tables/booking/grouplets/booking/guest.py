from gnr.web.gnrbaseclasses import BaseComponent

info = dict(caption='Guest', code='guest', priority=2)


class Grouplet(BaseComponent):
    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, table='test.booking')
        fb.field('guest_name', lbl='Guest Name', colspan=2, width='100%',
                 validate_notnull=True)
        fb.field('guest_email', lbl='Email', validate_notnull=True)
        fb.field('guest_phone', lbl='Phone')
        fb.field('document_type', tag='filteringSelect',
                 values='id_card:ID Card,passport:Passport,driving_license:Driving License',
                 lbl='Document Type')
        fb.field('document_number', lbl='Document Number')
