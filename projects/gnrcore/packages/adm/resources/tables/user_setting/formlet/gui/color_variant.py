from gnr.web.gnrbaseclasses import BaseComponent
from gnr.web.gnrwebpage import UNSET_COLOR_VARIANT

info = {
    "caption": "!![en]Color variant",
    "iconClass": "painbrush",
    "editing_path": "sys.theme"
}


class Formlet(BaseComponent):
    py_requires = 'th/th'

    def flt_main(self, pane):
        pane.div('!![en]Color changes will take effect after page reload',
                 font_size='.85em', color='var(--text-secondary)', padding='4px 0 8px')
        fb = pane.formlet(cols=1, border_spacing='4px')
        color_variants = self.getAvailableColorVariants(unset_option='application')
        default_color = self.getPreference('theme.color_variant', pkg='sys') \
                        or self.color_variant or ''
        theme_default = self.getAvailableColorVariants(unset_option='theme').split(',')[0].split(':', 1)[1]
        fb.filteringSelect(value='^.color_variant',
                           values=color_variants,
                           lbl='!![en]Color variant',
                           placeholder=default_color.capitalize() or theme_default)
        fb.dataController('SET .color_variant = null;', color_variant='^.color_variant',
                          _if=f'color_variant=="{UNSET_COLOR_VARIANT}"')
