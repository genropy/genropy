const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

// genro.dev.formbuilder builds either the legacy table (label on the left) or
// a formlet gridbox (label on top). The choice comes from the explicit
// `formlet` attribute, else from the experimental instance flag
// use_formlets_in_js_fb that the server puts in startArgs.useFormletsInJsFb.
// genro.dlg.prompt, and so ask/askParameters, goes through it.

function createPage(useFormlets) {
    const context = {console, gnr: {}, genro: {}};
    context.dojo = {
        declare(name, base, members) {
            function Declared(...args) {
                if (Object.hasOwn(members, 'constructor')) members.constructor.apply(this, args);
            }
            Declared.prototype = Object.assign(Object.create(Object.prototype), members);
            const names = name.split('.');
            let namespace = context;
            for (const part of names.slice(0, -1)) namespace = namespace[part] ||= {};
            namespace[names.at(-1)] = Declared;
            return Declared;
        }
    };
    vm.createContext(context);
    const sourceDir = process.env.GNR_JS_SOURCE || path.join(__dirname, '../gnr_d11/js');
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'genro_dev.js', 'genro_dlg.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    const genro = context.genro;
    const relativeData = [];
    genro.startArgs = useFormlets === undefined ? {} : {useFormletsInJsFb: useFormlets};
    genro.mainGenroWindow = {genro};
    genro._pageLocals = {};
    genro.locale = () => 'en-US';
    genro.getFromStorage = () => null;
    genro.setInStorage = () => {};
    genro.serverCall = (method, kw) => kw.txt;
    genro.getDataNode = () => null;
    genro.setData = () => {};
    genro.wdg = {wdgByDtype: (dtype) => ({D: 'dateTextBox', N: 'numberTextBox'})[dtype] || 'textbox'};
    genro.dev = new context.gnr.GnrDevHandler();
    genro.dlg = new context.gnr.GnrDlgHandler();
    const dialogs = [];
    genro.dlg.quickDialog = () => {
        const dlg = {center: fakeNode('center'), bottom: fakeNode('bottom'),
            show_action() {}, getParentNode: () => ({widget: {}})};
        dialogs.push(dlg);
        return dlg;
    };

    function fakeNode(tag, attr) {
        const node = {tag, attr: attr || {}, children: []};
        node._ = (childTag, attrOrLabel, maybeAttr) => {
            const attrs = typeof attrOrLabel === 'string' ? (maybeAttr || {}) : (attrOrLabel || {});
            const child = fakeNode(childTag, {...attrs});
            node.children.push(child);
            return child;
        };
        node.getParentNode = () => ({
            attr: node.attr,
            setRelativeData: (datapath, value) => relativeData.push([datapath, value])
        });
        return node;
    }

    function fieldsContainer() {
        const box = dialogs.at(-1).center.children.at(-1);
        return box.children.find((child) => child.tag !== 'div');
    }
    return {context, genro, dialogs, fakeNode, fieldsContainer, relativeData};
}

const FIELDS = [
    {name: 'myvalue', lbl: 'My value', validate_notnull: true, value: '^.myvalue'},
    {name: 'mycolor', lbl: 'Color', wdg: 'combobox', values: 'orange,green,blue', value: '^.mycolor'}
];

function promptFields(genro, kw) {
    genro.dlg.prompt('Which one', Object.assign({widget: FIELDS.map((f) => ({...f}))}, kw));
}

test('without the instance flag the fields go in the legacy formbuilder table', () => {
    const {genro, fieldsContainer} = createPage();
    promptFields(genro);
    const container = fieldsContainer();
    assert.equal(container.tag, 'table');
    const labels = container.children[0].children.flatMap((tr) => tr.children)
        .filter((td) => td.attr._class === 'gnrfieldlabel');
    assert.deepEqual(labels.map((td) => td.attr.innerHTML), ['My value', 'Color']);
});

test('the instance flag turns the fields into a formlet with labels on top', () => {
    const {genro, fieldsContainer} = createPage(true);
    promptFields(genro);
    const container = fieldsContainer();
    assert.equal(container.tag, 'gridbox');
    assert.equal(container.attr._class, 'formlet');
    assert.equal(container.attr.columns, 1);
    assert.equal(container.attr.datapath, '.promptvalue');
    assert.deepEqual(container.children.map((c) => [c.tag, c.attr.lbl]),
        [['textbox', 'My value'], ['combobox', 'Color']]);
    for (const field of container.children) {
        assert.equal(field.attr.lbl_text_align, undefined);
        assert.equal(field.attr.lbl_side, undefined);
    }
    assert.equal(container.children[0].attr.validate_notnull, true);
});

test('an explicit formlet=false wins over the instance flag', () => {
    const {genro, fieldsContainer} = createPage(true);
    promptFields(genro, {formlet: false});
    assert.equal(fieldsContainer().tag, 'table');
});

test('an explicit formlet=true wins over a missing instance flag', () => {
    const {genro, fieldsContainer} = createPage(false);
    promptFields(genro, {formlet: true});
    assert.equal(fieldsContainer().tag, 'gridbox');
});

test('cols becomes the formlet column count', () => {
    const {genro, fieldsContainer} = createPage(true);
    promptFields(genro, {cols: 2});
    assert.equal(fieldsContainer().attr.columns, 2);
});

test('a single-field prompt is a one-cell formlet bound to promptvalue', () => {
    const {genro, fieldsContainer} = createPage(true);
    genro.dlg.prompt('Change title', {lbl: 'Title', wdg_width: '20em'});
    const container = fieldsContainer();
    assert.equal(container.tag, 'gridbox');
    assert.equal(container.attr.datapath, undefined);
    assert.equal(container.children.length, 1);
    const [field] = container.children;
    assert.equal(field.tag, 'textbox');
    assert.equal(field.attr.lbl, 'Title');
    assert.equal(field.attr.value, '^.promptvalue');
    assert.equal(field.attr.width, '20em');
});

test('a message above the fields stays outside the formlet', () => {
    const {genro, dialogs} = createPage(true);
    genro.dlg.prompt('Which one', {msg: 'Pick one', widget: FIELDS.map((f) => ({...f}))});
    const box = dialogs.at(-1).center.children.at(-1);
    assert.equal(box.attr.padding, null);
    assert.deepEqual(box.children.map((c) => c.tag), ['div', 'gridbox']);
    assert.equal(box.children[0].attr.innerHTML, 'Pick one');
});

test('formlet addField keeps colspan, sets default_value and hides the whole cell', () => {
    const {genro, fakeNode, relativeData} = createPage();
    const grid = genro.dev.formlet(fakeNode('div'), 3, {gap: '4px'});
    assert.equal(grid.attr.columns, 3);
    assert.equal(grid.attr.gap, '4px');
    const field = grid.addField('textbox', {value: '^.notes', lbl: 'Notes', colspan: 2,
        default_value: 'hello', td_width: '10px', hidden: '^.nonotes'});
    assert.equal(field.attr.colspan, 2);
    assert.equal(field.attr.td_width, undefined);
    assert.equal(field.attr.default_value, undefined);
    assert.equal(field.attr.box_hidden, '^.nonotes');
    assert.deepEqual(relativeData, [['^.notes', 'hello']]);
});

test('askParameters forwards formlet from the ask definition', () => {
    const {genro, fieldsContainer} = createPage(false);
    genro.dlg.askParameters(() => {}, {title: 'Ask', formlet: true,
        fields: [{name: 'when', lbl: 'When', dtype: 'D'}]}, {when: '2026-10-19'});
    const container = fieldsContainer();
    assert.equal(container.tag, 'gridbox');
    assert.deepEqual(container.children.map((c) => [c.attr.tag, c.attr.lbl, c.attr.value]),
        [['dateTextBox', 'When', '^.when']]);
});

test('formbuilder follows the instance flag and drops table-only attributes', () => {
    const {genro, fakeNode} = createPage(true);
    const fb = genro.dev.formbuilder(fakeNode('div'), 2, {border_spacing: '6px', fld_width: '100%',
        lbl_color: '#666', lbl_text_align: 'right', datapath: '.record'});
    assert.equal(fb.tag, 'gridbox');
    assert.equal(fb.attr.columns, 2);
    assert.equal(fb.attr.datapath, '.record');
    for (const key of ['border_spacing', 'fld_width', 'lbl_color', 'lbl_text_align']) {
        assert.equal(fb.attr[key], undefined, key);
    }
    const field = fb.addField('textbox', {value: '^.code', lbl: 'Code', lbl_vertical_align: 'top'});
    assert.equal(field.attr.lbl_color, '#666');
    assert.equal(field.attr.lbl_text_align, undefined);
    assert.equal(field.attr.lbl_vertical_align, undefined);
});

test('formbuilder without the flag stays a table', () => {
    const {genro, fakeNode} = createPage();
    assert.equal(genro.dev.formbuilder(fakeNode('div'), 1, {border_spacing: '6px'}).tag, 'tbody');
    assert.equal(genro.dev.formbuilder(fakeNode('div'), 1).tag, 'tbody');
});

test('formlet:false keeps a toolbar formbuilder a table whatever the flag', () => {
    const {genro, fakeNode} = createPage(true);
    assert.equal(genro.dev.formbuilder(fakeNode('div'), 3, {formlet: false, border_spacing: '1px'}).tag, 'tbody');
});

test('formlet:true asks for a formlet without the flag', () => {
    const {genro, fakeNode} = createPage(false);
    assert.equal(genro.dev.formbuilder(fakeNode('div'), 1, {formlet: true}).tag, 'gridbox');
});
