# -*- coding: utf-8 -*-

"Mobyt service test"

from gnr.core.gnrdecorator import public_method

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_0_translationtest(self, pane):
        "Please configure a blank translation service (aws or yandex) and then test it here"
        bc = pane.borderContainer(height='250px')
        left = bc.contentPane(region='left', width='40%')
        fb_l = left.formbuilder(cols=1,border_spacing='3px')
        fb_l.textbox(value='^.what', width='100%', height='180px', lbl='Text to translate', default='Ciao Mondo')
        fb_l.filteringSelect(value='^.from_language', lbl='Language From', values='it,en,es,fr', default='it')
        fb_l.filteringSelect(value='^.to_language', lbl='Language To', values='it,en,es,fr', default='en')
        
        center = bc.borderContainer(region='center')
        center.button('Translate ->').dataRpc('.translation', self.translateText, 
                    what='=.what', from_language='=.from_language', to_language='=.to_language')
        
        right = bc.borderContainer(region='right', width='40%')
        fb_r = right.formbuilder(cols=1,border_spacing='3px')
        fb_r.simpleTextArea(value='^.translation', width='100%', height='180px', lbl='Translated text', 
                            readOnly=True, hidden='^.translation?=!#v')

    @public_method
    def translateText(self, what=None, from_language=None, to_language=None):
        translation_service = self.site.getService('translation')
        assert translation_service,'set in siteconfig the service for translations'
        result = translation_service.translate(what=what, to_language=to_language, from_language=from_language)
        return result