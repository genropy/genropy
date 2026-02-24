info = dict(caption='Altimetria', code='altimetria', priority=1)

class Grouplet(object):
    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px', table='glbl.comune')
        fb.field('zona_altimetrica')
        fb.field('altitudine')
        fb.field('comune_montano')
