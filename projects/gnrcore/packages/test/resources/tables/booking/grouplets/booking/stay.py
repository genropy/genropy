from gnr.web.gnrbaseclasses import BaseComponent

info = dict(caption='Stay', code='stay', priority=1)


class Grouplet(BaseComponent):
    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, table='test.booking')
        fb.field('check_in', tag='dateTextBox', lbl='Check-in',
                 validate_notnull=True)
        fb.field('check_out', tag='dateTextBox', lbl='Check-out',
                 validate_notnull=True)
        fb.field('room_type', tag='filteringSelect',
                 values='single:Single,double:Double,suite:Suite,family:Family',
                 lbl='Room Type', validate_notnull=True)
        fb.field('num_guests', tag='numberTextBox', lbl='Guests')
