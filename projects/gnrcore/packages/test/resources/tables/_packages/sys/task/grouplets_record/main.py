from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Main', priority=1, locationpath='record')

    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=1, table='sys.task')
        fb.field('task_name')
        fb.field('command')
