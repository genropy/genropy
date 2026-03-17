/*
 * module gnr_tracebackviewer : Traceback Bag renderer
 *
 * Renders a tracebackBag (as produced by gnrlang.tracebackBag)
 * into readable, interactive HTML with expandable frames and locals.
 *
 * API:
 *   gnr.tracebackViewer.render(bag, targetNode)
 *   gnr.tracebackViewer.toHtml(bag)  -> HTML string
 *
 * The bag structure expected:
 *   root (Bag)
 *     "module method name line N" (Bag)
 *       module, filename, file_hash, lineno, name, line
 *       locals (Bag) -> key/value pairs
 */

(function(){

    /* CSS is now in gnrbase_css/14_gnr_traceback.css — loaded by the framework */

    function esc(s){
        var d = document.createElement('div');
        d.textContent = s;
        return d.innerHTML;
    }

    function extractFrames(bag){
        if(!bag){ return []; }
        if(bag.getItem && bag.getItem('root')){
            var root = bag.getItem('root');
            if(root && root.forEach){ bag = root; }
        }
        var frames = [];
        var errorMessages = [];
        bag.forEach(function(node){
            var val = node.getValue ? node.getValue() : node._value;
            if(val && val.forEach && val.getItem && val.getItem('lineno')){
                frames.push(val);
            } else {
                errorMessages.push(String(val || node.label));
            }
        });
        return {frames: frames, errors: errorMessages};
    }

    function renderLocals(localsBag){
        if(!localsBag || !localsBag.len || localsBag.len() === 0){ return ''; }
        var count = localsBag.len();
        var rows = [];
        localsBag.forEach(function(node){
            var k = node.label;
            var v = String(node.getValue ? node.getValue() : (node._value != null ? node._value : 'None'));
            var isSpecial = v.charAt(0) === '*' && v.charAt(v.length - 1) === '*';
            if(v.length > 200){ v = v.substring(0, 200) + '...'; }
            var cls = isSpecial ? ' gnr-tb-loc-special' : '';
            rows.push('<tr><td class="gnr-tb-loc-name">' + esc(k) + '</td>' +
                       '<td class="gnr-tb-loc-value' + cls + '">' + esc(v) + '</td></tr>');
        });
        return '<div class="gnr-tb-locals">' +
            '<div class="gnr-tb-locals-hdr" onclick="this.parentElement.classList.toggle(\'expanded\')">' +
            '<span class="gnr-tb-locals-arrow">&#9654;</span> Local variables (' + count + ')' +
            '</div>' +
            '<table class="gnr-tb-locals-tbl">' +
            '<thead><tr><th>Name</th><th>Value</th></tr></thead>' +
            '<tbody>' + rows.join('') + '</tbody></table></div>';
    }

    function renderFrame(frameBag, index, isLast){
        var g = function(k){ var v = frameBag.getItem(k); return v != null ? String(v) : ''; };
        var module = g('module');
        var filename = g('filename');
        var fileHash = g('file_hash');
        var lineno = g('lineno');
        var name = g('name');
        var line = g('line');
        var localsBag = frameBag.getItem('locals');

        var openAttr = isLast ? ' open' : '';
        var hasLocals = localsBag && localsBag.len && localsBag.len() > 0;
        var localsHtml = hasLocals ? renderLocals(localsBag) : '';
        var localsBadge = hasLocals ?
            ' <span class="gnr-tb-locals-badge">' + localsBag.len() + ' vars</span>' : '';
        var hashHtml = fileHash ?
            ' <span class="gnr-tb-hash" title="SHA256">' + esc(fileHash) + '</span>' : '';
        var nameHtml = name ?
            ' <span class="gnr-tb-func">' + esc(name) + '</span>' : '';
        var codeHtml = line ?
            '<pre class="gnr-tb-code">' + esc(line) + '</pre>' : '';
        var filenameHtml = filename ?
            '<div class="gnr-tb-filename" title="' + esc(filename) + '">' + esc(filename) + '</div>' : '';

        return '<details class="gnr-tb-frame"' + openAttr + '>' +
            '<summary class="gnr-tb-summary">' +
            '<span class="gnr-tb-num">#' + index + '</span>' +
            '<span class="gnr-tb-module">' + esc(module) + '</span>' +
            '<span class="gnr-tb-sep">:</span>' +
            '<span class="gnr-tb-lineno">' + esc(lineno) + '</span>' +
            nameHtml + hashHtml + localsBadge +
            '</summary>' +
            '<div class="gnr-tb-body">' +
            filenameHtml + codeHtml + localsHtml +
            '</div></details>';
    }

    function toHtml(bag, options){
        if(!bag){ return '<p style="color:#888; font-style:italic;">No traceback available.</p>'; }
        options = options || {};
        var data = extractFrames(bag);
        var frames = data.frames;
        var errors = data.errors;
        var parts = [];
        var titleHtml = options.title ?
            '<span class="gnr-tb-toolbar-title">' + esc(options.title) + '</span>' : '';
        parts.push('<div class="gnr-tb-toolbar">' +
            titleHtml +
            '<button class="gnr-tb-btn gnr-tb-btn-copy">Copy All</button>' +
            '<button class="gnr-tb-btn gnr-tb-btn-expand">Expand All</button>' +
            '<button class="gnr-tb-btn gnr-tb-btn-collapse">Collapse All</button>' +
            '</div>');

        parts.push('<div class="gnr-tb-frames">');
        for(var i = 0; i < frames.length; i++){
            parts.push(renderFrame(frames[i], i, i === frames.length - 1));
        }
        for(var j = 0; j < errors.length; j++){
            parts.push('<div class="gnr-tb-errmsg">' + esc(errors[j]) + '</div>');
        }
        parts.push('</div>');
        return parts.join('\n');
    }

    function copyToClipboard(text){
        if(navigator.clipboard && window.isSecureContext){
            return navigator.clipboard.writeText(text);
        }
        var ta = document.createElement('textarea');
        ta.value = text;
        ta.style.cssText = 'position:fixed;left:-9999px';
        document.body.appendChild(ta);
        ta.select();
        try{ document.execCommand('copy'); }catch(e){}
        document.body.removeChild(ta);
        return Promise.resolve();
    }

    function bindToolbar(container, bag){
        var expandBtn = container.querySelector('.gnr-tb-btn-expand');
        var collapseBtn = container.querySelector('.gnr-tb-btn-collapse');
        var copyBtn = container.querySelector('.gnr-tb-btn-copy');
        if(expandBtn){
            expandBtn.onclick = function(){
                container.querySelectorAll('.gnr-tb-frame').forEach(function(d){ d.open = true; });
            };
        }
        if(collapseBtn){
            collapseBtn.onclick = function(){
                container.querySelectorAll('.gnr-tb-frame').forEach(function(d){ d.open = false; });
            };
        }
        if(copyBtn){
            copyBtn.onclick = function(){
                if(!bag){ return; }
                var xml = bag.toXml();
                copyToClipboard(xml).then(function(){
                    copyBtn.textContent = 'Copied!';
                    setTimeout(function(){ copyBtn.textContent = 'Copy All'; }, 1500);
                }).catch(function(){
                    copyBtn.textContent = 'Failed';
                    setTimeout(function(){ copyBtn.textContent = 'Copy All'; }, 1500);
                });
            };
        }
    }

    function sizeFrames(targetNode){
        var toolbar = targetNode.querySelector('.gnr-tb-toolbar');
        var frames = targetNode.querySelector('.gnr-tb-frames');
        if(!toolbar || !frames){ return; }
        var containerHeight = targetNode.clientHeight || targetNode.parentNode.clientHeight;
        var toolbarHeight = toolbar.offsetHeight;
        if(containerHeight > 0){
            frames.style.height = (containerHeight - toolbarHeight) + 'px';
        }
    }

    function render(bag, targetNode, options){
        if(typeof targetNode === 'string'){
            targetNode = document.getElementById(targetNode);
        }
        targetNode.className = (targetNode.className || '') + ' gnr-tb';
        targetNode.style.height = '100%';
        targetNode.innerHTML = toHtml(bag, options);
        bindToolbar(targetNode, bag);
        setTimeout(function(){ sizeFrames(targetNode); }, 50);
    }

    // Export
    if(!window.gnr){ window.gnr = {}; }
    window.gnr.tracebackViewer = {
        render: render,
        toHtml: toHtml
    };

})();
