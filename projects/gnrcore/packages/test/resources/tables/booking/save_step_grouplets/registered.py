from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Registered', priority=4)

    def grouplet_main(self, pane, **kwargs):
        pane.div(template='<b>$guest_name</b> · $room_type from $check_in · $total_amount',
                 datasource='^#FORM.record', margin_bottom='8px')
        fb = pane.formlet(cols=1, table='test.booking')
        fb.field('notes', tag='simpleTextArea', width='100%', height='60px')
