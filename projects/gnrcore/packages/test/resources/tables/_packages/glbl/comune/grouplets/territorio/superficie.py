info = dict(caption='Superficie e costa', code='superficie', priority=2)

class Grouplet(object):
    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px', table='glbl.comune')
        fb.field('superficie')
        fb.field('litoraneo')
