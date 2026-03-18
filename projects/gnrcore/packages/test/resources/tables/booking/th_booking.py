from gnr.web.gnrbaseclasses import BaseComponent


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
            grouplet_remote_num_guests="=.num_guests",
            saveMainFormOnComplete=True)

    def th_options(self):
        return dict(dialog_height='300px',dialog_width='500px',showtoolbar=False)
