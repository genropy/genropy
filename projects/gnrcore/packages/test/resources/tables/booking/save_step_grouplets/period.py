from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Period', priority=1)

    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, table='test.booking')
        fb.field('check_in', tag='dateTextBox', validate_notnull=True)
        fb.field('check_out', tag='dateTextBox')
        fb.field('room_type', tag='filteringSelect',
                 values='single:Single,double:Double,suite:Suite')
        fb.field('num_guests', tag='numberTextBox')
