from gnr.web.gnrbaseclasses import BaseComponent

class PrivacyPreferencePane(BaseComponent):

    def privacyPreferencePane(self, parent, title='!![en]Privacy', datapath='.privacy', **kwargs):
        bc = parent.borderContainer(datapath=datapath, title=title, height='100%', **kwargs)
        self.privacyText(bc.contentPane(region='center'))
        self.privacyConsents(bc.contentPane(region='bottom', height='50%'))

    def privacyText(self, pane, **kwargs):
        pane.ckeditor('^.privacy_policy', **kwargs)


    def privacyConsents(self, pane, **kwargs):
        grid = pane.quickGrid(value='^.consents')
        grid.tools('delrow,addrow',title='!![en]Consents')
        grid.column('code', width='8em', name='!![en]Code', edit=True)
        grid.column('description', width='auto', name='!![en]Description', edit=True)
        grid.column('mandatory', width='6em', dtype='B', name='!![en]Mandatory', edit=True)
            