/*
 * module genro_speech : Web Speech API helper
 *
 * Wraps webkitSpeechRecognition / SpeechRecognition with a simple
 * start/stop interface and per-call options (language, callbacks).
 *
 * API:
 *   genro.speech.isAvailable()
 *   genro.speech.start({lang, onResult, onError, onEnd, interimResults, continuous})
 *     returns { stop(), recognition }
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
    }

});
