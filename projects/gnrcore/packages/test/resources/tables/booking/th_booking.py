from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method


class View(BaseComponent):

    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('guest_name', width='15em')
        r.fieldcell('room_type', width='8em', name='Room')
        r.fieldcell('check_in', width='8em')
        r.fieldcell('check_out', width='8em')
        r.fieldcell('total_amount', width='8em', name='Total')

    def th_order(self):
        return 'check_in:d'

    def th_query(self):
        return dict(column='guest_name', op='contains', val='')


class Form(BaseComponent):
    py_requires = 'gnrcomponents/grouplet/grouplet:GroupletHandler'

    def th_form(self, form):
        form.center.contentPane().groupletWizard(
            table='test.booking',
            value='^.record',
            frameCode='booking_wizard',
            completeLabel='Complete Booking',
            grouplet_remote_num_guests="=#FORM.record.num_guests",
            saveMainFormOnComplete=True)

    def th_options(self):
        return dict(dialog_height='300px',dialog_width='500px',showtoolbar=False)


class ViewStack(BaseComponent):
    """View for the redtopic wizard probe: same shape as a ratio-sized
    dialog view (windowRatio + max_width instead of fixed dialog sizes)."""

    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('guest_name', width='15em')
        r.fieldcell('room_type', width='8em', name='Room')

    def th_order(self):
        return 'check_in:d'

    def th_query(self):
        return dict(column='guest_name', op='contains', val='')

    def th_options(self):
        return dict(widget='dialog', dialog_windowRatio=0.9,
                    dialog_max_width='620px')


class FormStack(BaseComponent):
    """Form for the redtopic wizard probe: a stackContainer page split
    driven by a record flag, the wizard on the first page — the same shape
    as a state-driven document form."""
    py_requires = 'gnrcomponents/grouplet/grouplet:GroupletHandler'

    def th_form(self, form):
        sc = form.center.stackContainer(selectedPage='^.record._vista')
        bc = sc.borderContainer(pageName='bozza')
        bc.contentPane(region='center').groupletWizard(
            table='test.booking',
            value='^.record',
            grouplets_root='redgrouplets',
            frameCode='redstack_wizard',
            completeLabel='Fine')
        sc.borderContainer(pageName='emessa').contentPane(
            region='center', overflow='auto').div('Issued document page')

    @public_method
    def th_onLoading(self, record, newrecord, loadingParameters, recInfo):
        record['_vista'] = 'bozza'

    def th_options(self):
        return dict(showtoolbar=False)
