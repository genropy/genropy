from gnr.web.gnrbaseclasses import BaseComponent

class PrivacyPreferencePane(BaseComponent):
    py_requires = "gnrcomponents/framegrid:FrameGrid"

    def privacyPreferencePane(self, parent, title='!![en]Privacy', datapath='.privacy', **kwargs):
        bc = parent.borderContainer(datapath=datapath, title=title, height='100%', **kwargs)
        self.privacyText(bc.contentPane(region='center'))
        self.privacyConsents(bc.contentPane(region='bottom', height='50%'))

    def privacyText(self, pane, **kwargs):
        pane.ckeditor('^.privacy_policy', **kwargs)

    def struct_privacy_consents(self, struct):
        r = struct.view().rows()
        r.cell('code', width='8em', name='!![en]Code', edit=True)
        r.cell('description', width='auto', name='!![en]Description', edit=True)
        r.cell('mandatory', width='6em', dtype='B', name='!![en]Mandatory', edit=True)
            
    def privacyConsents(self, pane, **kwargs):
        pane.bagGrid(struct=self.struct_privacy_consents, datapath='.consents', height='100%', width='100%', **kwargs)