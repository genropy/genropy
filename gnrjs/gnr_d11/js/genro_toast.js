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
        this._injectStyles();
        this._createContainer();
        dojo.subscribe('gnrToast', this, 'show');
    },

    _createContainer: function(){
        this.container = document.createElement('div');
        this.container.id = 'gnr-toast-container';
        document.body.appendChild(this.container);
    },

    _injectStyles: function(){
        var css = [
            '#gnr-toast-container {',
            '  position: fixed; top: 16px; right: 16px; z-index: var(--z-flash, 99999);',
            '  display: flex; flex-direction: column; gap: 8px;',
            '  pointer-events: none;',
            '}',
            '.gnr-toast {',
            '  display: flex; align-items: flex-start; gap: 10px;',
            '  min-width: 300px; max-width: 420px;',
            '  padding: 14px 16px; border-radius: var(--radius-controls, 8px);',
            '  background: var(--surface-color, white); position: relative; overflow: hidden;',
            '  box-shadow: var(--shadow-dialog, 0 4px 24px rgba(0,0,0,0.18), 0 1px 4px rgba(0,0,0,0.10));',
            '  pointer-events: auto; cursor: pointer;',
            '  font-size: var(--font-size, 14px); font-family: inherit;',
            '  transform: translateX(calc(100% + 20px)); opacity: 0;',
            '  animation: gnr-toast-in 0.35s cubic-bezier(0.21, 1.02, 0.73, 1) forwards;',
            '  will-change: transform, opacity;',
            '}',
            '.gnr-toast.gnr-toast-out {',
            '  animation: gnr-toast-out 0.28s cubic-bezier(0.06, 0.71, 0.55, 1) forwards;',
            '}',
            '@keyframes gnr-toast-in {',
            '  to { transform: translateX(0); opacity: 1; }',
            '}',
            '@keyframes gnr-toast-out {',
            '  from { transform: translateX(0); opacity: 1; }',
            '  to { transform: translateX(calc(100% + 20px)); opacity: 0; }',
            '}',
            /* Positioned toast: centered on target element */
            '.gnr-toast.gnr-toast-positioned {',
            '  position: absolute; z-index: var(--z-flash, 99999);',
            '  transform: scale(0.85); opacity: 0;',
            '  animation: gnr-toast-pop-in 0.3s cubic-bezier(0.21, 1.02, 0.73, 1) forwards;',
            '}',
            '.gnr-toast.gnr-toast-positioned.gnr-toast-out {',
            '  animation: gnr-toast-pop-out 0.25s cubic-bezier(0.06, 0.71, 0.55, 1) forwards;',
            '}',
            '@keyframes gnr-toast-pop-in {',
            '  to { transform: scale(1); opacity: 1; }',
            '}',
            '@keyframes gnr-toast-pop-out {',
            '  from { transform: scale(1); opacity: 1; }',
            '  to { transform: scale(0.85); opacity: 0; }',
            '}',
            '.gnr-toast-icon { flex-shrink: 0; width: 20px; height: 20px; margin-top: 1px; }',
            '.gnr-toast-body { flex: 1; min-width: 0; }',
            '.gnr-toast-title {',
            '  font-size: 0.93em; font-weight: 600; color: var(--text-primary, #1a1a1a);',
            '  margin: 0 0 2px 0; line-height: 1.3;',
            '}',
            '.gnr-toast-message {',
            '  font-size: 0.93em; color: var(--text-secondary, #555); margin: 0;',
            '  line-height: 1.4; word-break: break-word;',
            '}',
            '.gnr-toast-close {',
            '  flex-shrink: 0; width: 18px; height: 18px;',
            '  opacity: 0.35; transition: opacity 0.15s; margin-top: 1px;',
            '}',
            '.gnr-toast:hover .gnr-toast-close { opacity: 0.7; }',
            '.gnr-toast-progress {',
            '  position: absolute; bottom: 0; left: 0; height: 3px;',
            '  animation: gnr-toast-progress linear forwards;',
            '}',
            '@keyframes gnr-toast-progress {',
            '  from { width: 100%; } to { width: 0%; }',
            '}',
            '.gnr-toast[data-level="info"]    { border-left: 4px solid var(--accent-color, #3b82f6); }',
            '.gnr-toast[data-level="info"]    .gnr-toast-icon { color: var(--accent-color, #3b82f6); }',
            '.gnr-toast[data-level="info"]    .gnr-toast-progress { background: var(--accent-color, #3b82f6); }',
            '.gnr-toast[data-level="success"] { border-left: 4px solid var(--status-ok, #22c55e); }',
            '.gnr-toast[data-level="success"] .gnr-toast-icon { color: var(--status-ok, #22c55e); }',
            '.gnr-toast[data-level="success"] .gnr-toast-progress { background: var(--status-ok, #22c55e); }',
            '.gnr-toast[data-level="warning"] { border-left: 4px solid var(--status-warning, #f59e0b); }',
            '.gnr-toast[data-level="warning"] .gnr-toast-icon { color: var(--status-warning, #f59e0b); }',
            '.gnr-toast[data-level="warning"] .gnr-toast-progress { background: var(--status-warning, #f59e0b); }',
            '.gnr-toast[data-level="error"]   { border-left: 4px solid var(--status-error, #ef4444); }',
            '.gnr-toast[data-level="error"]   .gnr-toast-icon { color: var(--status-error, #ef4444); }',
            '.gnr-toast[data-level="error"]   .gnr-toast-progress { background: var(--status-error, #ef4444); }'
        ].join('\n');
        var style = document.createElement('style');
        style.textContent = css;
        document.head.appendChild(style);
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
