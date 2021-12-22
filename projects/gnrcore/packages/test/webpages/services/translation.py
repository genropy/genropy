# -*- coding: utf-8 -*-

"Mobyt service test"

from gnr.core.gnrdecorator import public_method

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_0_translationtest(self, pane):
        "Please configure a blank translation service and then test it here"
        fb = pane.formbuilder(cols=1,border_spacing='3px')
        fb.textbox(value='^.what', width='100%', height='200px', lbl='Text to translate')
        fb.filteringSelect(value='^.from_language', lbl='Language From', values='it,en,es,fr')
        fb.filteringSelect(value='^.to_language', lbl='Language To', values='it,en,es,fr')
        fb.button('Translate',fire='.translate').dataRpc(self.translateText, 
                    what='=.what', from_language='=.from_language', to_language='=.to_language')
        fb.simpleTextArea(value='^.translation', width='100%', height='200px', lbl='Translated text', readOnly=True)

    @public_method
    def translateText(self, what=None, from_language=None, to_language=None):
        translation_service = self.site.getService('translation')
        assert translation_service,'set in siteconfig the service for translations'
        result = translation_service.translate(what=what, to_language=to_language, from_language=from_language)
        return(result)