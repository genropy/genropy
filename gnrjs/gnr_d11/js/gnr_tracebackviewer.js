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

    var CSS_INJECTED = false;

    var CSS = [
        '.gnr-tb { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; font-size: 13px; }',

        '.gnr-tb-frame { margin-bottom: 6px; border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden; }',
        '.gnr-tb-frame:last-of-type { border-color: #f87171; }',
        '.gnr-tb-frame[open] { border-color: #cbd5e1; }',

        '.gnr-tb-summary {',
        '  padding: 8px 14px; cursor: pointer; background: #fafbfc;',
        '  display: flex; align-items: center; gap: 8px;',
        '  list-style: none; user-select: none;',
        '}',
        '.gnr-tb-summary::-webkit-details-marker { display: none; }',
        '.gnr-tb-summary::before {',
        '  content: "\\25B6"; font-size: 9px; color: #999;',
        '  transition: transform 0.2s; flex-shrink: 0;',
        '}',
        '.gnr-tb-frame[open] > .gnr-tb-summary::before { transform: rotate(90deg); }',
        '.gnr-tb-summary:hover { background: #f0f4f8; }',

        '.gnr-tb-num {',
        '  background: #e5e7eb; color: #666; font-size: 11px;',
        '  padding: 2px 6px; border-radius: 4px; font-weight: 600;',
        '  font-family: "SF Mono", Menlo, monospace;',
        '}',
        '.gnr-tb-frame:last-of-type .gnr-tb-num { background: #fee2e2; color: #dc2626; }',

        '.gnr-tb-module { color: #2563eb; font-weight: 600; }',
        '.gnr-tb-sep { color: #ccc; }',
        '.gnr-tb-lineno { color: #888; font-family: "SF Mono", Menlo, monospace; font-size: 12px; }',
        '.gnr-tb-func { color: #7c3aed; font-weight: 500; }',
        '.gnr-tb-func::before { content: "in "; color: #999; font-weight: 400; }',

        '.gnr-tb-hash {',
        '  color: #9ca3af; font-family: "SF Mono", Menlo, monospace;',
        '  font-size: 10px; background: #f3f4f6; padding: 1px 5px; border-radius: 3px;',
        '}',

        '.gnr-tb-locals-badge {',
        '  background: #dbeafe; color: #2563eb; font-size: 10px;',
        '  padding: 1px 6px; border-radius: 10px; font-weight: 600; margin-left: auto;',
        '}',

        '.gnr-tb-body { padding: 10px 14px 14px; background: white; }',
        '.gnr-tb-filename {',
        '  color: #9ca3af; font-size: 11px; margin-bottom: 6px;',
        '  word-break: break-all; font-family: "SF Mono", Menlo, monospace;',
        '}',
        '.gnr-tb-code {',
        '  background: #1e293b; color: #e2e8f0; padding: 10px 14px;',
        '  border-radius: 6px; font-family: "SF Mono", Menlo, monospace;',
        '  font-size: 13px; overflow-x: auto; line-height: 1.5; margin-bottom: 6px;',
        '}',

        '.gnr-tb-locals {',
        '  margin-top: 6px; border: 1px solid #e5e7eb; border-radius: 6px; overflow: hidden;',
        '}',
        '.gnr-tb-locals-hdr {',
        '  padding: 6px 10px; background: #f8fafc; cursor: pointer;',
        '  font-size: 12px; color: #666; font-weight: 600;',
        '  display: flex; align-items: center; gap: 6px; user-select: none;',
        '}',
        '.gnr-tb-locals-hdr:hover { background: #f0f4f8; }',
        '.gnr-tb-locals-arrow {',
        '  font-size: 10px; transition: transform 0.2s; display: inline-block;',
        '}',
        '.gnr-tb-locals.expanded .gnr-tb-locals-arrow { transform: rotate(90deg); }',

        '.gnr-tb-locals-tbl {',
        '  width: 100%; border-collapse: collapse; font-size: 12px; display: none;',
        '}',
        '.gnr-tb-locals.expanded .gnr-tb-locals-tbl { display: table; }',

        '.gnr-tb-locals-tbl th {',
        '  text-align: left; padding: 5px 10px; background: #f1f5f9;',
        '  font-size: 11px; color: #666; text-transform: uppercase;',
        '  letter-spacing: 0.3px; border-bottom: 1px solid #e5e7eb;',
        '}',
        '.gnr-tb-locals-tbl td {',
        '  padding: 4px 10px; border-bottom: 1px solid #f1f5f9; vertical-align: top;',
        '}',
        '.gnr-tb-locals-tbl tr:last-child td { border-bottom: none; }',
        '.gnr-tb-locals-tbl tr:hover { background: #f8fafc; }',
        '.gnr-tb-loc-name {',
        '  font-family: "SF Mono", Menlo, monospace; font-weight: 600;',
        '  color: #334155; white-space: nowrap; width: 1%;',
        '}',
        '.gnr-tb-loc-value {',
        '  font-family: "SF Mono", Menlo, monospace; color: #555;',
        '  word-break: break-all; max-width: 0;',
        '}',
        '.gnr-tb-loc-special { color: #9ca3af; font-style: italic; }',

        '.gnr-tb-errmsg {',
        '  background: #fef2f2; color: #dc2626; padding: 12px 16px;',
        '  border-radius: 8px; font-family: "SF Mono", Menlo, monospace;',
        '  font-size: 14px; font-weight: 600; margin-top: 10px;',
        '  border: 1px solid #fecaca; line-height: 1.5;',
        '}',

        '.gnr-tb-toolbar {',
        '  display: flex; justify-content: flex-end; gap: 6px; margin-bottom: 10px;',
        '}',
        '.gnr-tb-btn {',
        '  padding: 4px 10px; border: 1px solid #ddd; border-radius: 6px;',
        '  background: #f8f9fa; font-size: 11px; cursor: pointer; color: #555;',
        '}',
        '.gnr-tb-btn:hover { background: #e9ecef; border-color: #ccc; }'
    ].join('\n');

    function injectCss(){
        if(CSS_INJECTED){ return; }
        var style = document.createElement('style');
        style.textContent = CSS;
        document.head.appendChild(style);
        CSS_INJECTED = true;
    }

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

    function toHtml(bag){
        if(!bag){ return '<p style="color:#888; font-style:italic;">No traceback available.</p>'; }
        var data = extractFrames(bag);
        var frames = data.frames;
        var errors = data.errors;
        var parts = [];

        parts.push('<div class="gnr-tb-toolbar">' +
            '<button class="gnr-tb-btn" onclick="this.closest(\'.gnr-tb\').querySelectorAll(\'.gnr-tb-frame\').forEach(function(d){d.open=true;})">Expand All</button>' +
            '<button class="gnr-tb-btn" onclick="this.closest(\'.gnr-tb\').querySelectorAll(\'.gnr-tb-frame\').forEach(function(d){d.open=false;})">Collapse All</button>' +
            '</div>');

        for(var i = 0; i < frames.length; i++){
            parts.push(renderFrame(frames[i], i, i === frames.length - 1));
        }
        for(var j = 0; j < errors.length; j++){
            parts.push('<div class="gnr-tb-errmsg">' + esc(errors[j]) + '</div>');
        }
        return parts.join('\n');
    }

    function render(bag, targetNode){
        injectCss();
        if(typeof targetNode === 'string'){
            targetNode = document.getElementById(targetNode);
        }
        targetNode.className = (targetNode.className || '') + ' gnr-tb';
        targetNode.innerHTML = toHtml(bag);
    }

    // Export
    if(!window.gnr){ window.gnr = {}; }
    window.gnr.tracebackViewer = {
        render: render,
        toHtml: toHtml,
        injectCss: injectCss
    };

})();
