const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

// An unlabeled checkbox (or button) of a formlet with labels on top gets an
// invisible placeholder label only when a labeled field shares its grid row:
// alone on its row the placeholder is just an empty band (#1658). A checkbox
// with no visible label box shows the doc button of its column itself, beside
// its side label: a placeholder label is hidden, so it cannot host it.

function createContext() {
    const context = {console, File: function() {}, gnr: {}, genro: {}};
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
            // genro_widgets.js extends dijit classes this harness does not load
            Declared.prototype = Object.assign(Object.create(base && base.prototype ? base.prototype : Object.prototype), members);
            Declared.prototype.constructor = Declared;
            const names = name.split('.');
            let namespace = context;
            for (const part of names.slice(0, -1)) namespace = namespace[part] ||= {};
            namespace[names.at(-1)] = Declared;
            return Declared;
        }
    };
    context.dijit = {form: {ValidationTextBox: function() {}, CheckBox: function() {}}};
    vm.createContext(context);
    const sourceDir = process.env.GNR_JS_SOURCE || path.join(__dirname, '../gnr_d11/js');
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js', 'genro_widgets.js', 'genro_dev.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    const genro = context.genro;
    genro.startArgs = {};
    genro.wdg = {getHandler: () => null};
    let counter = 0;
    genro.time36Id = () => `id${counter++}`;
    // _T of the client formlet labels
    genro.mainGenroWindow = {genro};
    genro._pageLocals = {};
    genro.locale = () => 'en-US';
    genro.getFromStorage = () => null;
    genro.setInStorage = () => {};
    genro.serverCall = (method, kw) => kw.txt;
    genro.dev = new context.gnr.GnrDevHandler();
    return context;
}

const context = createContext();
// GnrDomSource._ tells the name from the attributes with instanceof Object:
// attributes must belong to the vm realm
const own = vm.runInContext('(attr) => Object.assign({}, attr)', context);

function serverFormlet(columns, fields) {
    // the source a pane.formlet() + field() sends: the checkbox lbl is already its label
    const root = new context.gnr.GnrDomSource();
    root.setBackRef();
    const grid = root._('gridbox', 'fb', own({_class: 'gnrgridbox formlet', columns}));
    for (const [tag, attr] of fields) grid._(tag, own(attr));
    return build(root.getNode('fb'));
}

function build(gridNode) {
    // what _buildChildren does on a gridbox: wrap each child, then build it,
    // and building converts its colspan (gridbox onChildBuilding)
    const gridbox = context.gnr.widgets.gridbox.prototype;
    const nodes = gridNode.getValue('static').getNodes();
    for (const node of nodes) {
        node.buildLblWrapper();
        gridbox.onChildBuilding(gridNode, node);
    }
    return [...nodes];
}

function placeholder(node) {
    return node.attr.tag === 'labledbox' && /formlet_placeholder_label/.test(node.attr._class || '');
}

const NAME = ['textbox', {lbl: 'Name', value: '^.name'}];
const CHECK = ['checkbox', {label: 'Active', value: '^.active'}];

test('a checkbox beside a labeled field gets the placeholder label', () => {
    const [name, check] = serverFormlet(2, [NAME, CHECK]);
    assert.equal(name.attr.label, 'Name');
    assert.ok(placeholder(check));
});

test('a full-row checkbox gets no placeholder label', () => {
    const nodes = serverFormlet(2, [
        ['textbox', {lbl: 'Name', colspan: 2}],
        ['checkbox', {label: 'Active', colspan: 2}],
        ['checkbox', {label: 'Public', colspan: 2}]
    ]);
    assert.deepEqual(nodes.map(placeholder), [false, false, false]);
    assert.equal(nodes[1].attr.tag, 'checkbox');
});

test('a checkbox wrapped onto a row of its own gets no placeholder label', () => {
    const nodes = serverFormlet(2, [NAME, ['textbox', {lbl: 'City'}], CHECK]);
    assert.equal(placeholder(nodes[2]), false);
});

test('a checkbox after a full-row field still lines up with the field on its row', () => {
    const nodes = serverFormlet(3, [['textbox', {lbl: 'Notes', colspan: 3}], CHECK, NAME]);
    assert.equal(placeholder(nodes[1]), true);
});

test('a statically hidden field takes no cell', () => {
    const nodes = serverFormlet(2, [NAME, ['textbox', {lbl: 'Parent', hidden: true}], CHECK]);
    assert.equal(placeholder(nodes[2]), true);
});

test('a checkbox next to buttons only gets no placeholder label', () => {
    const nodes = serverFormlet(2, [['button', {label: 'Go'}], CHECK]);
    assert.deepEqual(nodes.map(placeholder), [false, false]);
});

test('an explicit track list counts its tracks', () => {
    const nodes = serverFormlet('minmax(10em, 1fr) 2fr', [NAME, CHECK]);
    assert.equal(placeholder(nodes[1]), true);
    const alone = serverFormlet('1fr 2fr', [['textbox', {lbl: 'Name', colspan: 2}], CHECK]);
    assert.equal(placeholder(alone[1]), false);
});

test('without a predictable placement any labeled sibling keeps the placeholder', () => {
    const autoFit = serverFormlet('repeat(auto-fit, minmax(14em, 1fr))',
                                  [['textbox', {lbl: 'Name', colspan: 2}], ['checkbox', {label: 'Active', colspan: 2}]]);
    assert.equal(placeholder(autoFit[1]), true);
    const rowspan = serverFormlet(2, [['textbox', {lbl: 'Notes', rowspan: 2}], ['checkbox', {label: 'Active', colspan: 2}]]);
    assert.equal(placeholder(rowspan[1]), true);
});

test('the column count of a grid template', () => {
    const proto = context.gnr.GnrDomSourceNode.prototype;
    const count = (value) => proto._formletColumnCount(value);
    assert.equal(count(3), 3);
    assert.equal(count('repeat(3, 1fr)'), 3);
    assert.equal(count('repeat(2, 1fr 2fr) 5em'), 5);
    assert.equal(count('[start] 1fr [middle] 1fr [end]'), 2);
    assert.equal(count('repeat(auto-fill, 10em)'), null);
});

test('the doc address of a placeholder-labeled checkbox stays on the checkbox', () => {
    const doc = 'field:pkg.tbl:active';
    const [name, check] = serverFormlet(2, [['textbox', {lbl: 'Name', docAddress: 'field:pkg.tbl:name'}],
                                            ['checkbox', {label: 'Active', docAddress: doc}]]);
    assert.equal(name.attr.docAddress, 'field:pkg.tbl:name');
    assert.ok(placeholder(check));
    assert.equal(check.attr.docAddress, undefined);
    assert.equal(check._contentNode.attr.docAddress, doc);
});

test('a client-built formlet checkbox lines up only beside a labeled field', () => {
    const root = new context.gnr.GnrDomSource();
    root.setBackRef();
    const fb = context.genro.dev.formlet(root, 2, own({}));
    fb.addField('textbox', own({lbl: 'Name', value: '^.name'}));
    const beside = fb.addField('checkbox', own({lbl: 'Urgent', value: '^.urgent'})).getParentNode();
    assert.deepEqual([beside.attr.label, beside.attr.lbl], ['Urgent', undefined]);
    fb.addField('checkbox', own({lbl: 'Done', value: '^.done', colspan: 2}));
    const nodes = build(root.getNode('#0'));
    assert.deepEqual(nodes.map(placeholder), [false, true, false]);
});

function fakeElement(tag) {
    const element = {tag, children: [], attributes: {}, listeners: {}, style: {}, className: ''};
    element.setAttribute = (name, value) => { element.attributes[name] = value; };
    element.addEventListener = (type, callback) => { element.listeners[type] = callback; };
    element.appendChild = (child) => { element.children.push(child); child.parentNode = element; return child; };
    element.replaceChild = (newChild, oldChild) => {
        element.children[element.children.indexOf(oldChild)] = newChild;
        newChild.parentNode = element;
    };
    return element;
}

function createCheckbox(inlineDoc, style) {
    context.genro.startArgs = {inlineDoc};
    const tracked = [];
    const opened = [];
    context.document = {createElement: fakeElement};
    context.genro.wdg.create = (tag, parent) => parent.appendChild(fakeElement(tag));
    context.genro.dlg = {docTrack: (domNode, address) => tracked.push(address),
                         openDoc: (domNode, address, kw) => opened.push([address, kw])};
    const root = new context.gnr.GnrDomSource();
    root.setBackRef();
    root._('checkbox', 'flag', own({label: 'Active', field_name_long: 'Active', docAddress: 'field:pkg.tbl:active'}));
    const sourceNode = root.getNode('flag');
    sourceNode.hasDynamicAttr = () => false;
    const handler = context.gnr.widgets.CheckBox.prototype;
    const attributes = {...sourceNode.attr};
    const savedAttrs = handler.creating(attributes, sourceNode);
    const parent = fakeElement('div');
    const widget = {id: 'cb', domNode: parent.appendChild(fakeElement('div'))};
    Object.assign(widget.domNode.style, style);
    handler.created(widget, savedAttrs, sourceNode);
    return {attributes, widget, wrapper: sourceNode._gnrcheckbox_wrapper, tracked, opened};
}

test('a checkbox with a doc address shows the doc button beside its label', () => {
    const {attributes, wrapper, tracked, opened} = createCheckbox(true);
    assert.equal(attributes.docAddress, undefined);
    assert.deepEqual(wrapper.children.map((child) => child.tag), ['div', 'label', 'div']);
    const button = wrapper.children[2];
    assert.match(button.className, /helperbutton/);
    assert.deepEqual(tracked, ['field:pkg.tbl:active']);
    button.listeners.click({preventDefault() {}, stopPropagation() {}});
    assert.equal(opened[0][0], 'field:pkg.tbl:active');
    assert.equal(opened[0][1].title, 'Active');
    assert.equal(opened[0][1].tooltip, true);
});

test('without the inline docs a checkbox draws no doc button', () => {
    const {attributes, wrapper, tracked} = createCheckbox(false);
    assert.equal(attributes.docAddress, undefined);
    assert.deepEqual(wrapper.children.map((child) => child.tag), ['div', 'label']);
    assert.deepEqual(tracked, []);
});

test('the grid placement of a checkbox goes to its wrapper, the grid item', () => {
    // an unwrapped formlet checkbox with colspan=2 would otherwise take one column
    const {widget, wrapper} = createCheckbox(false, {gridColumn: 'span 2', width: '3em'});
    assert.equal(wrapper.style.gridColumn, 'span 2');
    assert.equal(widget.domNode.style.gridColumn, '');
    assert.equal(widget.domNode.style.width, '3em');
    assert.equal(wrapper.style.gridRow, undefined);
});
