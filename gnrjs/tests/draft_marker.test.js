const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

function createForm(draftMarker) {
    const context = {console, File: function() {}, gnr: {}, genro: {}};
    context.dojo = {
        Deferred: function() {},
        eval,
        hitch: (object, method) => (typeof method === 'string' ? object[method] : method).bind(object),
        forEach: (items, callback) => Array.prototype.forEach.call(items || [], callback),
        some: (items, callback) => Array.prototype.some.call(items || [], callback),
        toJson: JSON.stringify,
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
    const classes = new Set();
    const sourceNode = Object.create(context.gnr.GnrDomSourceNode.prototype);
    sourceNode.getDomNode = () => null;
    context.genro.dom = {
        setClass(where, cls, set) {
            assert.equal(where, sourceNode);
            if (set) {
                classes.add(cls);
            } else {
                classes.delete(cls);
            }
        }
    };
    const form = Object.create(context.gnr.GnrFrmHandler.prototype);
    form.sourceNode = sourceNode;
    if (arguments.length) {
        form.draftMarker = draftMarker;
    }
    return {form, marks: () => Array.from(classes).sort()};
}

test('draftMarker false leaves a draft form unmarked', () => {
    const s = createForm(false);
    s.form.updateDraftMarker(true);
    assert.deepEqual(s.marks(), []);
});

test("draftMarker 'bar' marks the form without choosing a corner", () => {
    const s = createForm('bar');
    s.form.updateDraftMarker(true);
    assert.deepEqual(s.marks(), ['form_draft']);
});

for (const pos of ['tr', 'tl', 'br', 'bl']) {
    test(`draftMarker '${pos}' marks the form with that corner`, () => {
        const s = createForm(pos);
        s.form.updateDraftMarker(true);
        assert.deepEqual(s.marks(), ['draft_marker_' + pos, 'form_draft']);
    });
}

for (const [name, build] of [['true', () => createForm(true)], ['unset', () => createForm()]]) {
    test(`draftMarker ${name} falls back to the top right corner`, () => {
        const s = build();
        s.form.updateDraftMarker(true);
        assert.deepEqual(s.marks(), ['draft_marker_tr', 'form_draft']);
    });
}

for (const draftMarker of [false, 'bar', 'tr', true, undefined]) {
    test(`leaving draft clears every mark with draftMarker ${JSON.stringify(draftMarker)}`, () => {
        const s = createForm(draftMarker);
        s.form.updateDraftMarker(true);
        s.form.updateDraftMarker(false);
        assert.deepEqual(s.marks(), []);
    });
}
