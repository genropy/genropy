# -*- coding: utf-8 -*-

"Speech input test page"

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_0_simpleTextArea(self, pane):
        """SimpleTextArea with speech and silence timeout settings"""
        fb = pane.formbuilder(cols=2, border_spacing='3px')
        fb.numberTextBox(value='^.silence_timeout', lbl='Silence timeout (ms)',
                         default=2500, width='100px')
        fb.simpleTextArea(value='^.note', height='300px', width='400px',
                         lbl='Note', speech=True,
                         speech_silenceTimeout='^.silence_timeout',
                         speech_stopWords='stop,fine,basta')
        fb.div('^.note', colspan=2)

    def test_3_speechSynthesis(self, pane):
        """Text-to-speech: type text, pick language, press Speak"""
        fb = pane.formbuilder(cols=2, border_spacing='3px')
        fb.textbox(value='^.speak_text', lbl='Text to speak',
                   width='300px')
        fb.textbox(value='^.speak_lang', lbl='Language (BCP-47)',
                   placeholder='e.g. it-IT, en-US')
        fb.button('Speak',
                  action='genro.speech.speak(text, {lang: lang || undefined})',
                  text='=.speak_text', lang='=.speak_lang')
        fb.button('Cancel',
                  action='genro.speech.cancel()')
        fb.div('^.speaking_status', lbl='Speaking')
        pane.dataController("""
            var check = function(){
                SET .speaking_status = genro.speech.isSpeaking() ? 'Speaking...' : 'Idle';
            };
            check();
            var iv = setInterval(check, 300);
            setTimeout(function(){ clearInterval(iv); }, 30000);
        """, _fired='^.speak_text')

    def test_4_voiceList(self, pane):
        """List available synthesis voices, optionally filtered by language"""
        fb = pane.formbuilder(cols=2, border_spacing='3px')
        fb.textbox(value='^.voice_lang', lbl='Filter by language',
                   placeholder='e.g. it, en')
        fb.button('Get Voices',
                  action="""var voices = genro.speech.getVoices(lang || undefined);
                            var lines = voices.map(function(v){
                                return v.name + ' (' + v.lang + ')';
                            });
                            SET .voice_list = lines.join('\\n');""",
                  lang='=.voice_lang')
        fb.simpleTextArea(value='^.voice_list', lbl='Voices',
                          height='200px', width='400px', readonly=True)
