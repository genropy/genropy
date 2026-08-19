from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Header', priority=1)

    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px',
                          table='test.myticket')
        fb.field('subject', colspan=2, width='100%',
                 validate_notnull=True)
        fb.field('ticket_date')
        fb.field('status', tag='filteringSelect',
                 values='open:Open,in_progress:In Progress,closed:Closed')
