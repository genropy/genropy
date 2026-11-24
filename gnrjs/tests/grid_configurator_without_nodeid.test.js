const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

function createGrid() {
    const context = {console, File: function() {}, gnr: {}, genro: {}, setTimeout, navigator: {}, window: {}, document: {},
                     dijit: {_Widget: function() {}, layout: {}, form: {}}};
    context.dojo = {
        Deferred: function() {},
        eval,
        isIE: 0,
        version: {major: 1, minor: 1},
        require() {},
        provide() {},
        hitch: (object, method) => (typeof method === 'string' ? object[method] : method).bind(object),
        forEach: (items, callback) => Array.prototype.forEach.call(items || [], callback),
        indexOf: (items, value) => Array.prototype.indexOf.call(items || [], value),
        toJson: JSON.stringify,
        declare(name, bases, members) {
            const base = Array.isArray(bases) ? bases[0] : bases;
            function Declared(...args) {
                if (base) base.apply(this, args);
                if (Object.hasOwn(members, 'constructor')) members.constructor.apply(this, args);
            }
            Declared.prototype = Object.assign(Object.create(base ? base.prototype : Object.prototype), members);
            Declared.prototype.constructor = Declared;
            const names = name.split('.');
            let namespace = context;
            for (const part of names.slice(0, -1)) namespace = namespace[part] ||= {};
            namespace[names.at(-1)] = Declared;
            return Declared;
        }
    };
    vm.createContext(context);
    const root = process.env.GNR_ROOT || path.join(__dirname, '../..');
    const sourceDir = process.env.GNR_JS_SOURCE || path.join(root, 'gnrjs/gnr_d11/js');
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js', 'genro_widgets.js',
                            'genro_components.js', 'genro_grid.js', 'genro_wdg.js', 'genro_src.js', 'genro.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    const configurator = 'resources/common/th/th_viewconfigurator.js';
    vm.runInContext(readFileSync(path.join(root, configurator), 'utf8'), context, {filename: configurator});
    context._T = str => str;
    const {gnr} = context;
    const src = Object.create(gnr.GnrSrcHandler.prototype);
    Object.assign(src, {_main: new gnr.GnrDomSource(), _index: {}});
    const tooltips = [];
    const genro = Object.create(gnr.GenroClient.prototype);
    Object.assign(genro, {
        src,
        wdg: {getHandler: () => null},
        dlg: {quickTooltipPane: (kw, cb) => tooltips.push(kw)},
        grid_configurator: context.genro_plugin_grid_configurator
    });
    context.genro = genro;
    // a configurable grid built without a nodeId
    src._main._('div', 'body', {tag: 'div'});
    src._main.getNode('body').getValue()._('quickgrid', 'grid', {tag: 'quickgrid', configurable: true, structpath: '.struct'});
    const gridNode = src._main.getNode('body').getValue().getNode('grid');
    gridNode.absDatapath = () => 'grid.struct';
    const widget = Object.create(gnr.widgets.NewIncludedView.prototype);
    widget.sourceNode = gridNode;
    return {genro, gridNode, widget, tooltips};
}

test('genro.nodeBySourceNodeId resolves a source node by its numeric or string id', () => {
    const s = createGrid();
    assert.ok(s.genro.nodeBySourceNodeId(s.gridNode._id) === s.gridNode, 'numeric id');
    assert.ok(s.genro.nodeBySourceNodeId(s.gridNode.getStringId()) === s.gridNode, 'string id');
});

test('the column set tooltip of a configurable grid without nodeId finds its grid', () => {
    const s = createGrid();
    s.widget.mixin_configuratorColsetTooltip({code: 'main'}, {target: {}});
    assert.equal(s.tooltips.length, 1);
});
