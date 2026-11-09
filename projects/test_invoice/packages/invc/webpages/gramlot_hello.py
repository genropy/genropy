"""Public Hello World using only Python-authored Gramlot components."""
from gnr.web.gramlotpage import GramlotPage


class GnrCustomWebPage(GramlotPage):
    public = True
    title = 'Hello World · Gramlot'

    def main(self, root):
        root.data('name', 'World')
        root.data('opening.count', 0)
        root.dataController(
            "this.SET('opening.count', (this.getRelativeData('opening.count') || 0) + 1);",
            subscribe_changedStartArgs=True)
        panel = root.div(padding='24px', max_width='640px')
        panel.h1('Hello World')
        panel.p('A Gramlot page hosted by Genropy, without Dojo.')
        panel.textBox(value='^name', lbl='Your name', live=True)
        panel.div('^name', margin_top='12px')
        opening = panel.div(margin_top='12px')
        opening.span('Opening arguments received: ')
        opening.span('^opening.count')
        panel.p('Host services: .site and .db are available.'
                if self.site is not None and self.db is not None
                else 'Host services are unavailable.')
