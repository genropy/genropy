info = dict(caption='Statistiche', code='statistiche', priority=4)

class Grouplet(object):
    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px', table='glbl.comune')
        fb.field('popolazione_residente')
        fb.field('csl')
