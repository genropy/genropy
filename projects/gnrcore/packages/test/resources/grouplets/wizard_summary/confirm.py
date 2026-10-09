from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Confirm', priority=4)

    def grouplet_main(self, pane, **kwargs):
        pane.div('Check the summaries in the stepper, then confirm.',
                 color='#666', font_style='italic')
