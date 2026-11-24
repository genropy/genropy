const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

function createPage({isDeveloper = true} = {}) {
    const consoleWarnings = [];
    const toasts = [];
    const context = {console: {log() {}, warn: (...args) => consoleWarnings.push(args.join(' ')), error() {}},
                     gnr: {}, File: function() {}, window: {}, setTimeout, clearTimeout, dojox: {grid: {}}, dijit: {}};
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
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'genro.js', 'genro_widgets.js', 'gnrdomsource.js', 'genro_grid.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    const genro = Object.create(context.gnr.GenroClient.prototype);
    Object.assign(genro, {
        _sanitize_js: true, isDeveloper,
        dev: {addError: (message, type, show) => toasts.push({message, type, show})},
        format: v => v,
        dom: {getStyleDict: () => ({})},
        getData: () => undefined
    });
    context.genro = genro;
    return {context, genro, consoleWarnings, toasts};
}

function gridColumn(context, field, gridAttr = {nodeId: 'anagrafica_grid'}) {
    const proto = context.gnr.widgets.VirtualStaticGrid.prototype;
    const sourceNode = {
        attr: gridAttr,
        _id: 42,
        isPointerPath: context.gnr.GnrDomSourceNode.prototype.isPointerPath,
        currentFromDatasource: v => v,
        evaluateOnNode: d => d
    };
    const cellNode = {label: field, attr: {width: '10em'}, getParentNode: () => ({attr: {}})};
    const cell = proto.structFromBag_cell.call(proto, sourceNode, cellNode, new context.gnr.GnrBag());
    return function render(rowdata) {
        const grid = {rowCached: () => rowdata, currRenderedRow: rowdata, cellmap: {[field]: cell}};
        const cellObj = Object.assign(Object.create(proto), cell, {grid, customStyles: [], customClasses: []});
        return cell.formatter.call(cellObj, rowdata[field], 0);
    };
}

const handlerRow = i => ({stato: `<span onclick="apri('R${i}')">Riga ${i}</span>`});

test('a column emitting a handler on every row raises one toast naming the column', () => {
    const {context, toasts, consoleWarnings} = createPage();
    const render = gridColumn(context, 'stato');
    for (let i = 0; i < 100; i++) {
        assert.ok(!render(handlerRow(i)).includes('onclick'), 'the handler is still stripped on every row');
    }
    assert.equal(toasts.length, 1);
    assert.equal(toasts[0].type, 'CLIENT');
    assert.equal(toasts[0].show, true);
    assert.ok(toasts[0].message.includes('grid anagrafica_grid, column stato'), toasts[0].message);
    assert.ok(toasts[0].message.includes(`<code>&lt;span onclick="apri('R0')"&gt;Riga 0&lt;/span&gt;</code>`),
              toasts[0].message);
    assert.equal(consoleWarnings.length, 1);
    assert.ok(consoleWarnings[0].includes('in grid anagrafica_grid, column stato'));
    assert.ok(consoleWarnings[0].includes("apri('R0')"), 'the console keeps the full first content');
});

test('each faulty column of a grid warns once on its own', () => {
    const {context, toasts} = createPage();
    const stato = gridColumn(context, 'stato');
    const azioni = gridColumn(context, 'azioni');
    for (let i = 0; i < 5; i++) {
        stato(handlerRow(i));
        azioni({azioni: `<a onmouseover="x(${i})">a</a>`});
    }
    assert.deepEqual(toasts.map(t => t.message.match(/column (\w+)/)[1]), ['stato', 'azioni']);
});

test('the same field in two grids warns once per grid; a grid without nodeId uses its node id', () => {
    const {context, toasts} = createPage();
    gridColumn(context, 'stato')(handlerRow(1));
    gridColumn(context, 'stato', {})(handlerRow(2));
    gridColumn(context, 'stato', {})(handlerRow(3));
    assert.equal(toasts.length, 2);
    assert.ok(toasts[1].message.includes('grid n_42, column stato'));
});

test('a clean column raises nothing', () => {
    const {context, toasts, consoleWarnings} = createPage();
    const render = gridColumn(context, 'nome');
    assert.ok(render({nome: '<b>Mario</b>'}).includes('<b>Mario</b>'));
    assert.deepEqual(toasts, []);
    assert.deepEqual(consoleWarnings, []);
});

test('callers without a source keep the per-content dedup', () => {
    const {genro, toasts, consoleWarnings} = createPage();
    genro.safeHtmlContent('<div onclick="a()">x</div>');
    genro.safeHtmlContent('<div onclick="a()">x</div>');
    genro.safeHtmlContent('<div onclick="b()">x</div>');
    assert.equal(toasts.length, 2);
    assert.equal(consoleWarnings.length, 2);
    assert.ok(!toasts[0].message.includes(' in '));
});

test('a non-developer gets the console warning only', () => {
    const {context, toasts, consoleWarnings} = createPage({isDeveloper: false});
    const render = gridColumn(context, 'stato');
    render(handlerRow(1));
    render(handlerRow(2));
    assert.deepEqual(toasts, []);
    assert.equal(consoleWarnings.length, 1);
});
