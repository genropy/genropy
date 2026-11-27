const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

function loadRowEditor() {
    const context = {console, gnr: {}, genro: {}, setTimeout, navigator: {}, window: {}, document: {}};
    context.dojo = {
        require() {},
        provide() {},
        declare(name, bases, members) {
            function Declared() {}
            Declared.prototype = Object.assign({}, members);
            const names = name.split('.');
            let namespace = context;
            for (const part of names.slice(0, -1)) namespace = namespace[part] ||= {};
            namespace[names.at(-1)] = Declared;
            return Declared;
        }
    };
    vm.createContext(context);
    const sourceDir = process.env.GNR_JS_SOURCE || path.join(__dirname, '../gnr_d11/js');
    vm.runInContext(readFileSync(path.join(sourceDir, 'genro_wdg.js'), 'utf8'), context, {filename: 'genro_wdg.js'});
    return context.gnr.RowEditor;
}

// a grid over rows A, B, C; rowEditor is the editor of the row with the given pkey
function checkRowEditor({pkey, gnrediting = false, currentEditedRow = null}) {
    const RowEditor = loadRowEditor();
    const pkeys = ['A', 'B', 'C'];
    const redrawn = [];
    const grid = {
        gnrediting,
        currentEditedRow,
        indexByRowAttr: (attr, value) => pkeys.indexOf(value),
        updateRow: idx => redrawn.push(idx)
    };
    RowEditor.prototype.checkRowEditor.call({grid, rowId: pkey});
    return redrawn;
}

test('a row is redrawn when the grid is not editing', () => {
    assert.deepEqual(checkRowEditor({pkey: 'B'}), [1]);
});

test('the row being edited is left to endEdit', () => {
    assert.deepEqual(checkRowEditor({pkey: 'B', gnrediting: true, currentEditedRow: 1}), []);
});

test('another row is redrawn while a row is being edited', () => {
    assert.deepEqual(checkRowEditor({pkey: 'C', gnrediting: true, currentEditedRow: 1}), [2]);
});

test('a row that is not in the grid is not redrawn', () => {
    assert.deepEqual(checkRowEditor({pkey: 'Z'}), []);
});
