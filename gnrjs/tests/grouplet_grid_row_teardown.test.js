const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

function createGrid({minRows = 0} = {}) {
    const context = {console, File: function() {}, gnr: {}, genro: {}, setTimeout};
    context.dojo = {
        Deferred: function() {},
        eval,
        hitch: (object, method) => (typeof method === 'string' ? object[method] : method).bind(object),
        forEach: (items, callback) => Array.prototype.forEach.call(items || [], callback),
        some: (items, callback) => Array.prototype.some.call(items || [], callback),
        toJson: JSON.stringify,
        isIE: 0,
        declare(name, base, members) {
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
    const sourceDir = process.env.GNR_JS_SOURCE || path.join(__dirname, '../gnr_d11/js');
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js', 'genro_frm.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    const gridJs = path.join(__dirname, '../../resources/common/gnrcomponents/grouplet/grouplet_grid.js');
    vm.runInContext(readFileSync(gridJs, 'utf8'), context, {filename: 'grouplet_grid.js'});
    context._T = str => str;
    const Bag = context.gnr.GnrBag;
    const data = new Bag();
    const record = new Bag();
    const rows = new Bag();
    rows.setItem('r_1', new Bag({sigla: 'MI', nome: 'Milano'}));
    record.setItem('rows', rows);
    data.setItem('outer.record', record, {_pkey: 'LOM'});
    data.setItem('outer.controller', new Bag());
    data.setBackRef();
    context.genro._data = data;
    context.genro.getDataNode = p => data.getNode(p);
    context.genro.getData = p => data.getItem(p);
    const main = new context.gnr.GnrDomSource();
    context.genro.src = {_main: main, formsToUpdate: {}, nodeBySourceNodeId: id => main.findNodeById(id)};
    context.genro.wdg = {getHandler: () => null};
    const formNode = Object.create(context.gnr.GnrDomSourceNode.prototype);
    formNode.absDatapath = value => value[0] === '.' ? 'outer' + value : value;
    formNode.getParentNode = () => ({});
    const form = Object.create(context.gnr.GnrFrmHandler.prototype);
    Object.assign(form, {
        sourceNode: formNode,
        formDatapath: 'outer.record',
        controllerPath: 'outer.controller',
        pkeyPath: 'outer.pkey',
        gridEditors: {},
        _register: {},
        autoRegisterTags: {textbox: true},
        checkLastSavedTags: {},
        _status_list: [],
        allowSaveInvalid: false,
        isDisabled: () => false,
        disabledStatus: () => null,
        isProtectWrite: () => false,
        isNewRecord: () => false,
        registeredGridsStatus: () => null,
        publish: () => {},
        applyDisabledStatus: () => {}
    });
    form.resetInvalidFields();
    form.resetChanges();
    // the grid body with one mounted tile, as _renderTile leaves it
    main._('div', 'body', {tag: 'div'});
    const bodyNode = main.getNode('body');
    const asked = [];
    const controller = Object.create(context.gnr.GroupletGridController.prototype);
    Object.assign(controller, {
        bodyNode,
        tiles: {},
        layout: 'cards',
        minRows,
        addBtnDom: null,
        selectedPkey: null,
        dataStore: {deleteRowAsk: pkey => asked.push(pkey)}
    });
    const tile = new context.gnr.GroupletGridTile(controller, 'r_1');
    bodyNode.getValue()._('div', tile.tileLabel, {tag: 'div', datapath: '.r_1'});
    tile.tileNode = bodyNode.getValue().getNode(tile.tileLabel);
    tile.tileContent = tile.tileNode.getValue();
    tile.tileContent._('textbox', 'sigla', {tag: 'textbox', value: '^.sigla', validate_notnull: true});
    tile.mounted = true;
    tile.bodyMounted = true;
    controller.tiles.r_1 = tile;
    const field = tile.tileContent.getNode('sigla');
    field.form = form;
    field.updateValidationClasses = () => {};
    field.getElementLabel = () => 'Sigla';
    field.absDatapath = () => 'outer.record.rows.r_1.sigla';
    form.registerChild(field);
    field.setValidations();
    return {form, field, controller, bodyNode, asked};
}

test('destroying a tile whose field is invalid leaves the form valid and clean', () => {
    const s = createGrid();
    s.field.setValidationError({error: 'Required', warnings: [], required: true});
    s.form.updateInvalidField(s.field, 'outer.record.rows.r_1.sigla');
    s.form.dojoValidation({sourceNode: s.field}, false);
    assert.equal(s.form.isValid(), false);
    s.controller.selectedPkey = 'r_1';
    s.controller._destroyTile('r_1');
    assert.equal(s.bodyNode.getValue().getNode('_grtile_r_1'), null);
    assert.deepEqual(Object.keys(s.form._register), []);
    assert.equal(s.form.getInvalidFields().len(), 0);
    assert.equal(s.form.getInvalidDojo().len(), 0);
    assert.equal(s.form.isValid(), true);
    assert.equal(s.controller.selectedPkey, null);
    assert.deepEqual(Object.keys(s.controller.tiles), []);
});

test('minRows stops the delete before the dialog', () => {
    const kept = createGrid({minRows: 1});
    kept.controller._askAndDeleteItem('r_1');
    assert.deepEqual(kept.asked, []);
    const free = createGrid();
    free.controller._askAndDeleteItem('r_1');
    assert.deepEqual(free.asked, ['r_1']);
});
