from gnr.web.gnrbaseclasses import BaseComponent

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
        color_variants = self.getAvailableColorVariants()
        default_color = self.getPreference('theme.color_variant', pkg='sys') \
                        or self.color_variant or ''
        fb.filteringSelect(value='^.color_variant',
                           values=color_variants,
                           lbl='!![en]Color variant',
                           placeholder=default_color.capitalize() or 'None')
