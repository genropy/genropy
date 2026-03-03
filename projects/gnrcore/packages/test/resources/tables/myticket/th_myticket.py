from gnr.web.gnrbaseclasses import BaseComponent


class View(BaseComponent):
    py_requires = 'gnrcomponents/grouplet/grouplet:GroupletHandler'

    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('subject', width='20em')
        r.fieldcell('ticket_type', width='10em', name='Type')
        r.fieldcell('ticket_date', width='10em')
        r.fieldcell('status', width='8em')

    def th_order(self):
        return 'ticket_date:d'

    def th_query(self):
        return dict(column='subject', op='contains', val='')

    def th_options(self):
        return dict(
            addrow=self.gr_groupletAddrowMenu(table='test.myticket', field='ticket_type')
        )


class Form(BaseComponent):
    py_requires = 'gnrcomponents/grouplet/grouplet:GroupletHandler'

    def th_form(self, form):
        bc = form.center.borderContainer()
        top = bc.contentPane(region='top', datapath='.record')
        fb = top.formlet(cols=2, border_spacing='3px')
        fb.field('subject', colspan=2, width='100%')
        fb.field('ticket_type', readOnly=True, tag='div')
        fb.field('ticket_date')
        fb.field('status', tag='filteringSelect',
                 values='open:Open,in_progress:In Progress,closed:Closed')
        fb.field('description', colspan=2, width='100%', tag='simpleTextArea',
                 height='60px')
        bc.contentPane(region='center', datapath='.record.extra_data').grouplet(
            resource='=#FORM.record.ticket_type',
            table='test.myticket',showOnFormLoaded=True)

    def th_options(self):
        return dict(dialog_windowRatio=.9,
            form_add=self.gr_groupletAddrowMenu(table='test.myticket', field='ticket_type')
        )
