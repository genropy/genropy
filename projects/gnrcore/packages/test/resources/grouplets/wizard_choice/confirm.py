from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Confirm', priority=3)

    def grouplet_main(self, pane, **kwargs):
        pane.div('Go back to Kind: the chosen tile is still marked, a click moves on again.',
                 color='#666', font_style='italic')
