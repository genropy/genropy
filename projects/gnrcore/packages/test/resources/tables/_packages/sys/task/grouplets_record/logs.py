from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Logs', priority=2, locationpath='record')

    def grouplet_main(self, pane, **kwargs):
        # a datapath outside the grouplet record keeps the handler store out of it
        pane.contentPane(height='300px').dialogTableHandler(
            relation='@logs', maintable='sys.task',
            datapath='#FORM.task_logs', configurable=False)
