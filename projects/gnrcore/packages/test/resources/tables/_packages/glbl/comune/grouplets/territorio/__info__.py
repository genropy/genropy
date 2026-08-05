class GroupletTopic(object):
    def __info__(self):
        return dict(caption='Territorio', priority=3,
                    template='<div>${<span>Zona: <b>$altimetria.zona_altimetrica</b></span>}'
                             '${<span> | Alt. $altimetria.altitudine m</span>}'
                             '${<span> | $altimetria.comune_montano</span>}</div>'
                             '${<div>Superficie: $superficie.superficie kmq'
                             ' | Litoraneo: $superficie.litoraneo</div>}')
