/*
 * module genro_toast : Pure HTML/CSS toast notification system
 *
 * Replaces dojox.widget.Toaster with a modern, dependency-free
 * notification component.
 *
 * API:
 *   genro.toast.show({message, title, level, duration, target, onClose})
 *   genro.toast.dismiss(el)
 *
 * Levels: info, success, warning, error
 * target: optional sourceNode or DOM element — toast appears centered on it.
 *         When omitted, toast goes to the global top-right container.
 * Listens to dojo topic 'gnrToast' for pub/sub integration.
 */

dojo.declare("gnr.GnrToast", null, {

    ICONS: {
        info:    '<svg viewBox="0 0 20 20" fill="currentColor"><circle cx="10" cy="10" r="9" fill="none" stroke="currentColor" stroke-width="1.5"/><circle cx="10" cy="6.5" r="1.2"/><rect x="9" y="9" width="2" height="5.5" rx="1"/></svg>',
        success: '<svg viewBox="0 0 20 20" fill="currentColor"><circle cx="10" cy="10" r="9" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M6 10.5l2.5 2.5 5.5-5.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>',
        warning: '<svg viewBox="0 0 20 20" fill="currentColor"><path d="M10 1.5L0.5 17.5h19L10 1.5z" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><rect x="9" y="7" width="2" height="5" rx="1"/><circle cx="10" cy="14.5" r="1.2"/></svg>',
        error:   '<svg viewBox="0 0 20 20" fill="currentColor"><circle cx="10" cy="10" r="9" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M7 7l6 6M13 7l-6 6" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>'
    },

    CLOSE_ICON: '<svg viewBox="0 0 18 18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M5 5l8 8M13 5l-8 8"/></svg>',

    DURATIONS: {info: 4000, success: 3000, warning: 5000, error: 6000},

    LEVEL_MAP: {'message': 'info', 'fatal': 'error'},

    constructor: function(){
        this._createContainer();
        dojo.subscribe('gnrToast', this, 'show');
    },

    _createContainer: function(){
        this.container = document.createElement('div');
        this.container.id = 'gnr-toast-container';
        document.body.appendChild(this.container);
    },

    _resolveTarget: function(target){
        if(!target){ return null; }
        /* sourceNode (gnr bag node) → its DOM element */
        if(target.getDomNode){ return target.getDomNode(); }
        if(target.domNode){ return target.domNode; }
        /* already a DOM element */
        if(target.nodeType){ return target; }
        return null;
    },

    _centerOn: function(el, targetDom){
        var rect = targetDom.getBoundingClientRect();
        var ew = el.offsetWidth;
        var eh = el.offsetHeight;
        el.style.left = Math.round(rect.left + (rect.width - ew) / 2) + 'px';
        el.style.top = Math.round(rect.top + (rect.height - eh) / 2) + 'px';
    },

    show: function(opts){
        if(typeof opts === 'string'){
            opts = {message: opts};
        }
        var level = this.LEVEL_MAP[opts.level] || opts.level || 'info';
        var duration = opts.duration || this.DURATIONS[level] || 4000;
        var targetDom = this._resolveTarget(opts.target);

        var el = document.createElement('div');
        el.className = 'gnr-toast' + (targetDom ? ' gnr-toast-positioned' : '');
        el.setAttribute('data-level', level);

        var bodyHtml = '';
        if(opts.title){
            bodyHtml += '<p class="gnr-toast-title">' + opts.title + '</p>';
        }
        bodyHtml += '<p class="gnr-toast-message">' + (opts.message || '') + '</p>';

        el.innerHTML =
            '<span class="gnr-toast-icon">' + (this.ICONS[level] || this.ICONS.info) + '</span>' +
            '<div class="gnr-toast-body">' + bodyHtml + '</div>' +
            '<span class="gnr-toast-close">' + this.CLOSE_ICON + '</span>' +
            '<div class="gnr-toast-progress" style="animation-duration:' + duration + 'ms"></div>';

        if(opts.onClose){
            el._gnrToastOnClose = opts.onClose;
        }

        if(targetDom){
            document.body.appendChild(el);
            this._centerOn(el, targetDom);
        }else{
            this.container.appendChild(el);
        }

        var self = this;
        var timer = setTimeout(function(){ self.dismiss(el); }, duration);

        el.addEventListener('click', function(){
            clearTimeout(timer);
            self.dismiss(el);
        });
        el.addEventListener('mouseenter', function(){
            clearTimeout(timer);
            var bar = el.querySelector('.gnr-toast-progress');
            if(bar){ bar.style.animationPlayState = 'paused'; }
        });
        el.addEventListener('mouseleave', function(){
            var bar = el.querySelector('.gnr-toast-progress');
            if(bar){ bar.style.animationPlayState = 'running'; }
            timer = setTimeout(function(){ self.dismiss(el); }, 2000);
        });
        return el;
    },

    dismiss: function(el){
        if(el.classList.contains('gnr-toast-out')){ return; }
        el.classList.add('gnr-toast-out');
        var onClose = el._gnrToastOnClose;
        el.addEventListener('animationend', function(){
            if(el.parentNode){ el.parentNode.removeChild(el); }
            if(onClose){ onClose(); }
        });
    }
});
