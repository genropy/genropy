const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

function createContext() {
    const warnings = [];
    const context = {console: {log() {}, warn() {}, error() {}}, gnr: {}, File: function() {},
                     setTimeout, clearTimeout, dojox: {grid: {}}, dijit: {}};
    context.dojo = {
        eval, toJson: JSON.stringify, version: {major: 1, minor: 6},
        require() {}, provide() {}, Deferred: function() {}, connect() {}, subscribe() {},
        mixin: Object.assign, isString: s => typeof s === 'string',
        hitch: (object, method) => (typeof method === 'string' ? object[method] : method).bind(object),
        forEach: (items, callback) => Array.prototype.forEach.call(items || [], callback),
        some: (items, callback) => Array.prototype.some.call(items || [], callback),
        declare(name, base, members) {
            const bases = [].concat(base || []);
            function Declared(...args) {
                for (const b of bases) b.apply(this, args);
                if (Object.hasOwn(members, 'constructor')) members.constructor.apply(this, args);
            }
            Declared.prototype = Object.assign(Object.create(bases.length ? bases[0].prototype : Object.prototype),
                                               ...bases.slice(1).map(b => b.prototype), members);
            Declared.prototype.constructor = Declared;
            const names = name.split('.');
            let namespace = context;
            for (const part of names.slice(0, -1)) namespace = namespace[part] ||= {};
            namespace[names.at(-1)] = Declared;
            return Declared;
        }
    };
    vm.createContext(context);
    const sourceDir = process.env.GNR_JS_SOURCE || path.join(__dirname, '../gnr_d11/js');
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'genro_widgets.js', 'gnrdomsource.js', 'genro_grid.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    context.genro = {
        safeHtmlContent(str) {
            if (typeof str !== 'string') return str;
            const result = context.stripJsFromHtml(str);
            if (result !== str) warnings.push(str);
            return result;
        },
        format: v => v,
        dom: {getStyleDict: () => ({})},
        getData: () => undefined
    };
    return {context, warnings};
}

// A browser decodes the on* attribute value (HTML entities) before parsing it as JS: emulate both.
function decodeAttr(s) {
    return s.replace(/&#x([0-9a-f]+);/gi, (m, h) => String.fromCharCode(parseInt(h, 16)))
            .replace(/&#(\d+);/g, (m, d) => String.fromCharCode(+d))
            .replace(/&quot;/g, '"').replace(/&#39;|&apos;/g, "'").replace(/&lt;/g, '<')
            .replace(/&gt;/g, '>').replace(/&amp;/g, '&');
}
function handlersIn(html) {
    return [...html.matchAll(/\bon(\w+)\s*=\s*("([^"]*)"|'([^']*)')/gi)]
        .map(m => ({event: m[1], code: decodeAttr(m[3] ?? m[4])}));
}
function fire(handler, globals) {
    const calls = [];
    const sandbox = {event: {type: 'click'}, calls, ...globals};
    sandbox.alert = (...args) => calls.push(['alert', ...args]);
    vm.runInNewContext(handler.code, sandbox);
    return calls;
}

// The two anaci templates of the report (th_se_vendita_riga.py, th_crediti_assegnazione.py).
const SE_VENDITA_RIGA = `<div class="spc_celltpl servizio-acquistato $incluso_primario_classe">
    <div class="linguetta" style="background:$tipo_servizio_colore"></div>
    <div class="spc_tpl_titolo">$tpl_cella_titolo</div>
    <div class="trashableIfDraft iconbox trash servizio_cancellabile" onclick="genro.publish('cancella_riga_vendita',{eventInfo:genro.dom.getEventInfo(event)})">&nbsp;</div>
    <div><span class="spc_totale"> \${Totale  $totale&euro;}</span></div></div>`;
const CREDITI = `<div style='display:flex;'><div><div>$data_assegnazione</div><div style='font-size:0.9em'>$crediti_descrizione</div></div>
    <div>Crediti: $crediti_assegnati</div>
    \${<div onclick="anaci_app_companion.spostaCrediti('$id',event);"><span style="text-decoration:underline;">$spostamento</span></div>}</div>`;

function render(context, template, row, kw = {trustedMarkup: true}) {
    return context.dataTemplate(template, new context.gnr.GnrBag(row), null, null, kw);
}

test('anaci se_vendita_riga: the trash icon handler survives verbatim and fires', () => {
    const {context, warnings} = createContext();
    const html = render(context, SE_VENDITA_RIGA, {incluso_primario_classe: 'incluso', tipo_servizio_colore: 'red',
                                                   tpl_cella_titolo: '<b>Cena</b>', totale: 12});
    assert.ok(html.includes(`onclick="genro.publish('cancella_riga_vendita',{eventInfo:genro.dom.getEventInfo(event)})"`));
    assert.ok(html.includes('<b>Cena</b>'), 'HTML in a text-context value is still allowed');
    assert.ok(html.includes('Totale  12&euro;'));
    const published = [];
    const calls = fire(handlersIn(html)[0], {genro: {publish: (topic, kw) => published.push([topic, kw]),
                                                     dom: {getEventInfo: e => ({evt: e.type})}}});
    assert.equal(JSON.stringify(published), JSON.stringify([['cancella_riga_vendita', {eventInfo: {evt: 'click'}}]]));
    assert.deepEqual(calls, []);
    assert.deepEqual(warnings, []);
});

test('anaci crediti_assegnazione: the move-credits handler survives and receives the row id', () => {
    const {context, warnings} = createContext();
    const html = render(context, CREDITI, {data_assegnazione: '2026-01-01', crediti_descrizione: 'd',
                                           crediti_assegnati: 3, id: 'AB_12', spostamento: 'Sposta'});
    assert.ok(html.includes(`onclick="anaci_app_companion.spostaCrediti('AB\\x5f12',event);"`), html);
    const received = [];
    fire(handlersIn(html)[0], {anaci_app_companion: {spostaCrediti: (id, ev) => received.push([id, ev.type])}});
    assert.deepEqual(received, [['AB_12', 'click']]);
    assert.deepEqual(warnings, []);
    const noMove = render(context, CREDITI, {id: null, spostamento: 'Sposta', crediti_assegnati: 3});
    assert.equal(handlersIn(noMove).length, 0, '${...} block still disappears when its first field is empty');
});

test('payload 3: a quote breaking out of the JS string inside the template onclick is inert', () => {
    const {context, warnings} = createContext();
    const payload = "');alert(1);//";
    const html = render(context, CREDITI, {id: payload, spostamento: 'Sposta', crediti_assegnati: 1});
    const handlers = handlersIn(html);
    assert.equal(handlers.length, 1);
    const received = [];
    const calls = fire(handlers[0], {anaci_app_companion: {spostaCrediti: id => received.push(id)}});
    assert.deepEqual(received, [payload], 'the handler runs and gets the raw value as a string');
    assert.deepEqual(calls, [], 'alert never runs');
    assert.deepEqual(warnings, []);
});

test('an entity-encoded quote &#39; inside onclick is not decoded into a quote', () => {
    const {context} = createContext();
    const payload = "&#39;);alert(1);//";
    const html = render(context, CREDITI, {id: payload, spostamento: 'Sposta', crediti_assegnati: 1});
    const handlers = handlersIn(html);
    assert.equal(handlers.length, 1);
    const received = [];
    const calls = fire(handlers[0], {anaci_app_companion: {spostaCrediti: id => received.push(id)}});
    assert.deepEqual(received, [payload]);
    assert.deepEqual(calls, []);
});

test('payload 1: javascript: from a field into href/src is still rewritten by the final pass', () => {
    const {context, warnings} = createContext();
    const html = render(context, `<a href="$url" onclick="track('$url')">x</a><img src="$img">`,
                        {url: 'javascript:alert(1)', img: 'javascript:alert(2)'});
    assert.ok(html.includes('href="#"'), html);
    assert.ok(html.includes('src=""'), html);
    assert.ok(html.includes(`onclick="track('javascript\\x3aalert\\x281\\x29')"`), html);
    assert.equal(warnings.length, 1, 'the final pass reports what it stripped, once per cell');
});

test('payload 2: a handler split across two adjacent fields is assembled and stripped', () => {
    const {context, warnings} = createContext();
    const html = render(context, `<div onclick="ok()">$a$b</div>`, {a: '<img src=x o', b: 'nerror=alert(1)>'});
    assert.ok(!/onerror/i.test(html), html);
    assert.ok(html.includes('onclick="ok()"'), 'the template handler next to it is kept');
    assert.equal(warnings.length, 1);
});

test('<script> and a complete on* handler inside a value are stripped per value', () => {
    const {context} = createContext();
    const html = render(context, `<div class="c $cls" onclick="ok()">$txt</div>`,
                        {txt: '<script>alert(1)</script>Safe<img src=x onerror="alert(2)">',
                         cls: '" onmouseover="alert(3)'});
    assert.equal(handlersIn(html).length, 1);
    assert.equal(handlersIn(html)[0].code, 'ok()');
    assert.ok(!html.includes('<script'));
    assert.ok(html.includes('Safe'));
});

test('a field that IS the whole handler, or sits bare in JS code, never becomes code', () => {
    const {context} = createContext();
    const html = render(context, `<a onclick="$h">1</a><a onclick="go($n)">2</a><a onclick="go($s)">3</a>`,
                        {h: 'alert(1)', n: 42, s: '1);alert(1);('});
    const handlers = handlersIn(html);
    assert.equal(handlers.length, 3);
    const seen = [];
    let calls = [];
    for (const h of handlers) calls = calls.concat(fire(h, {go: v => seen.push(v)}));
    assert.deepEqual(calls, []);
    assert.deepEqual(seen, [42, '1);alert(1);(']);
});

test('a plain-object row and a mixed-case handler attribute take the same path', () => {
    const {context, warnings} = createContext();
    const html = context.dataTemplate(`<a OnClick="go('$id')">$id</a>`, {id: "');alert(1);//"}, null, null,
                                      {trustedMarkup: true});
    assert.ok(html.includes(`OnClick="go('\\x27\\x29\\x3balert\\x281\\x29\\x3b\\x2f\\x2f')">');alert(1);//</a>`), html);
    const seen = [];
    assert.deepEqual(fire(handlersIn(html)[0], {go: v => seen.push(v)}), []);
    assert.deepEqual(seen, ["');alert(1);//"]);
    assert.deepEqual(warnings, []);
});

test('backtick template literal inside a handler: ${ from a value stays text', () => {
    const {context} = createContext();
    const html = render(context, "<a onclick=\"go(`id-$id`)\">1</a>", {id: '${alert(1)}'});
    const seen = [];
    const calls = fire(handlersIn(html)[0], {go: v => seen.push(v)});
    assert.deepEqual(calls, []);
    assert.deepEqual(seen, ['id-${alert(1)}']);
});

test('without trustedMarkup dataTemplate is unchanged: raw value in the handler, no final pass', () => {
    const {context, warnings} = createContext();
    const html = render(context, CREDITI, {id: "');alert(1);//", spostamento: 'S', crediti_assegnati: 1}, {});
    assert.equal(html, "<div style='display:flex;'><div><div></div><div style='font-size:0.9em'></div></div>\n"
                       + "    <div>Crediti: 1</div>\n"
                       + `    <div onclick="anaci_app_companion.spostaCrediti('');alert(1);//',event);">`
                       + '<span style="text-decoration:underline;">S</span></div></div>');
    assert.deepEqual(warnings, []);
});

function gridCell(context, rowTemplateAttr, datasource) {
    const proto = context.gnr.widgets.VirtualStaticGrid.prototype;
    const sourceNode = {
        attr: {},
        isPointerPath: context.gnr.GnrDomSourceNode.prototype.isPointerPath,
        currentFromDatasource(v) { return this.isPointerPath(v) ? datasource[v.slice(1)] : v; },
        evaluateOnNode: d => d
    };
    const cellNode = {label: 'tpl', attr: {rowTemplate: rowTemplateAttr, width: '100%'},
                      getParentNode: () => ({attr: {}})};
    const cell = proto.structFromBag_cell.call(proto, sourceNode, cellNode, new context.gnr.GnrBag());
    return {cell, renderRow(rowdata) {
        const grid = {rowCached: () => rowdata, currRenderedRow: rowdata, cellmap: {tpl: cell}};
        const cellObj = Object.assign(Object.create(proto), cell, {grid, customStyles: [], customClasses: []});
        const v = proto.attributes_mixin_get.call(cellObj, 0);
        return cell.formatter.call(cellObj, v, 0);
    }};
}

test('grid: the anaci trash icon of a literal rowTemplate keeps its handler', () => {
    const {context, warnings} = createContext();
    const literal = gridCell(context, SE_VENDITA_RIGA, {});
    assert.equal(literal.cell._trustedRowTemplate, true);
    assert.equal(literal.cell._formats._trustedRowTemplate, true);
    const html = literal.renderRow({incluso_primario_classe: 'i', tipo_servizio_colore: 'red', tpl_cella_titolo: 't', totale: 1});
    assert.ok(html.startsWith('<div  class="cellContent"'));
    assert.equal(handlersIn(html).length, 1);
    assert.deepEqual(warnings, []);
});

test('grid: a literal rowTemplate is trusted end to end, its interpolated id inert', () => {
    const {context, warnings} = createContext();
    const row = {id: "');alert(1);//", spostamento: 'S', crediti_assegnati: 1, data_assegnazione: 'd', crediti_descrizione: 'x'};
    const literal = gridCell(context, CREDITI, {});
    const html = literal.renderRow(row);
    const handlers = handlersIn(html);
    assert.equal(handlers.length, 1);
    const received = [];
    assert.deepEqual(fire(handlers[0], {anaci_app_companion: {spostaCrediti: id => received.push(id)}}), []);
    assert.deepEqual(received, [row.id]);
    assert.deepEqual(warnings, []);
});

test('grid: a ^-bound rowTemplate keeps the final pass on the cell', () => {
    const {context, warnings} = createContext();
    const row = {id: 'AB_12', spostamento: 'S', crediti_assegnati: 1};
    const bound = gridCell(context, '^.tpl', {'.tpl': CREDITI});
    assert.equal(bound.cell._trustedRowTemplate, false);
    assert.equal(bound.cell._formats._trustedRowTemplate, undefined);
    assert.equal(bound.cell.rowTemplate, CREDITI);
    const html = bound.renderRow(row);
    assert.equal(handlersIn(html).length, 0);
    assert.equal(warnings.length, 1);
});
