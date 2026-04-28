/*
 * module genro_speech : Web Speech API helper
 *
 * Wraps both Web Speech APIs:
 *   - SpeechRecognition (audio -> text): start({...}) / stop()
 *   - SpeechSynthesis   (text -> audio): speak(text, {...}) / cancel()
 *
 * Recognition API:
 *   genro.speech.isAvailable()
 *   genro.speech.start({lang, onResult, onError, onEnd, interimResults, continuous})
 *     returns { stop(), recognition }
 *
 * Synthesis API:
 *   genro.speech.canSpeak()
 *   genro.speech.speak(text, {lang, rate, pitch, volume, voice, onEnd, onError, onStart})
 *     returns { utterance, cancel() }
 *   genro.speech.cancel()       // stop everything currently being spoken
 *   genro.speech.isSpeaking()
 *   genro.speech.getVoices(lang) // optional lang filter (substring match on voice.lang)
 *
 * onResult is invoked with the final transcript string each time a
 * final result becomes available. interim results are ignored unless
 * interimResults is true (in which case onResult receives both, with
 * a second boolean argument isFinal).
 */

dojo.declare("gnr.GnrSpeech", null, {

    _Recognition: function(){
        return window.SpeechRecognition || window.webkitSpeechRecognition;
    },

    isAvailable: function(){
        return !!this._Recognition();
    },

    canSpeak: function(){
        return !!window.speechSynthesis;
    },

    _resolveLang: function(lang){
        if(lang){
            return lang;
        }
        if(window.genro && genro.locale){
            try{
                var loc = genro.locale();
                if(loc){
                    return loc.replace('_', '-');
                }
            }catch(e){}
        }
        return undefined;
    },

    start: function(opts){
        opts = opts || {};
        var Recognition = this._Recognition();
        if(!Recognition){
            if(opts.onError){ opts.onError({error: 'not-supported'}); }
            return null;
        }
        var recognition = new Recognition();
        recognition.continuous = opts.continuous !== false;
        recognition.interimResults = !!opts.interimResults;
        var lang = this._resolveLang(opts.lang);
        if(lang){
            recognition.lang = lang;
        }
        recognition.onresult = function(event){
            var i = event.resultIndex;
            for(; i < event.results.length; i++){
                var res = event.results[i];
                var transcript = res[0].transcript;
                if(opts.onResult){
                    if(opts.interimResults){
                        opts.onResult(transcript, res.isFinal);
                    }else if(res.isFinal){
                        opts.onResult(transcript);
                    }
                }
            }
        };
        recognition.onerror = function(event){
            if(opts.onError){ opts.onError(event); }
        };
        recognition.onend = function(){
            if(opts.onEnd){ opts.onEnd(); }
        };
        try{
            recognition.start();
        }catch(e){
            if(opts.onError){ opts.onError({error: 'start-failed', exception: e}); }
            return null;
        }
        return {
            recognition: recognition,
            stop: function(){
                try{ recognition.stop(); }catch(e){}
            }
        };
    },

    speak: function(text, opts){
        opts = opts || {};
        if(!this.canSpeak()){
            if(opts.onError){ opts.onError({error: 'not-supported'}); }
            return null;
        }
        if(text == null || text === ''){
            return null;
        }
        var u = new SpeechSynthesisUtterance(String(text));
        var lang = this._resolveLang(opts.lang);
        if(lang){ u.lang = lang; }
        if(opts.rate != null){   u.rate   = opts.rate; }
        if(opts.pitch != null){  u.pitch  = opts.pitch; }
        if(opts.volume != null){ u.volume = opts.volume; }
        if(opts.voice){          u.voice  = opts.voice; }
        u.onstart = opts.onStart || null;
        u.onend   = opts.onEnd   || null;
        u.onerror = opts.onError || null;
        try{
            window.speechSynthesis.speak(u);
        }catch(e){
            if(opts.onError){ opts.onError({error: 'speak-failed', exception: e}); }
            return null;
        }
        return {
            utterance: u,
            cancel: function(){ window.speechSynthesis.cancel(); }
        };
    },

    cancel: function(){
        if(this.canSpeak()){
            window.speechSynthesis.cancel();
        }
    },

    isSpeaking: function(){
        return this.canSpeak() && window.speechSynthesis.speaking;
    },

    getVoices: function(lang){
        if(!this.canSpeak()){ return []; }
        var voices = window.speechSynthesis.getVoices() || [];
        if(!lang){ return voices; }
        return voices.filter(function(v){
            return v.lang && v.lang.toLowerCase().indexOf(lang.toLowerCase()) === 0;
        });
    }

});
