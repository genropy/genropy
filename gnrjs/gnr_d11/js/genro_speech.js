/*
 * module genro_speech : Web Speech API helper
 *
 * Wraps both Web Speech APIs:
 *   - SpeechRecognition (audio -> text): start({...}) / stop()
 *   - SpeechSynthesis   (text -> audio): speak(text, {...}) / cancel()
 *
 * Recognition API:
 *   genro.speech.isAvailable()
 *   genro.speech.start({lang, onResult, onSilence, onError, onEnd,
 *                       interimResults, continuous, silenceTimeout})
 *     returns { stop(), recognition }
 *
 *   silenceTimeout (ms, default 0 = disabled): when set, the recognition
 *     auto-stops after this many ms without a new final result.
 *   onSilence(lastTranscript): fired once just before the auto-stop
 *     triggered by silenceTimeout. Not fired on manual stop or error.
 *   onEnd(silenceFired): receives a boolean telling whether the end
 *     was caused by the silence timer.
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
        const Recognition = this._Recognition();
        if(!Recognition){
            if(opts.onError){ opts.onError({error: 'not-supported'}); }
            return null;
        }
        const recognition = new Recognition();
        recognition.continuous = opts.continuous !== false;
        recognition.interimResults = !!opts.interimResults;
        const lang = this._resolveLang(opts.lang);
        if(lang){
            recognition.lang = lang;
        }
        const silenceTimeout = opts.silenceTimeout || 0;
        const stopWords = (opts.stopWords || []).map(w => w.toLowerCase().trim()).filter(Boolean);
        let silenceTimer = null;
        let lastFinalTranscript = '';
        let silenceFired = false;
        let stopWordFired = false;
        const checkStopWords = (text) => {
            if(!stopWords.length){ return null; }
            const lower = text.toLowerCase();
            for(const word of stopWords){
                const idx = lower.lastIndexOf(word);
                if(idx >= 0){
                    return {word, idx};
                }
            }
            return null;
        };
        const clearSilenceTimer = () => {
            if(silenceTimer){
                clearTimeout(silenceTimer);
                silenceTimer = null;
            }
        };
        const armSilenceTimer = () => {
            if(silenceTimeout <= 0){ return; }
            clearSilenceTimer();
            silenceTimer = setTimeout(() => {
                silenceTimer = null;
                silenceFired = true;
                if(opts.onSilence){
                    opts.onSilence(lastFinalTranscript);
                }
                try{ recognition.stop(); }catch(e){}
            }, silenceTimeout);
        };
        recognition.onresult = (event) => {
            if(stopWordFired){ return; }
            let finalText = '';
            let interimText = '';
            for(const res of event.results){
                const transcript = res[0].transcript;
                if(res.isFinal){
                    finalText += transcript;
                }else{
                    interimText += transcript;
                }
            }
            const fullText = finalText + interimText;
            const match = checkStopWords(fullText);
            if(match){
                stopWordFired = true;
                clearSilenceTimer();
                const cleaned = fullText.substring(0, match.idx).trim();
                if(opts.onResult){
                    if(opts.interimResults){
                        opts.onResult(cleaned, '');
                    }else{
                        opts.onResult(cleaned);
                    }
                }
                try{ recognition.stop(); }catch(e){}
                return;
            }
            if(finalText){
                lastFinalTranscript = finalText;
                armSilenceTimer();
            }
            if(opts.onResult){
                if(opts.interimResults){
                    opts.onResult(finalText, interimText);
                }else if(finalText){
                    opts.onResult(finalText);
                }
            }
        };
        recognition.onerror = (event) => {
            clearSilenceTimer();
            if(opts.onError){ opts.onError(event); }
        };
        recognition.onend = () => {
            clearSilenceTimer();
            if(opts.onEnd){ opts.onEnd(silenceFired); }
        };
        try{
            recognition.start();
        }catch(e){
            if(opts.onError){ opts.onError({error: 'start-failed', exception: e}); }
            return null;
        }
        return {
            recognition,
            stop(){
                clearSilenceTimer();
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
