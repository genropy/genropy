const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

const root = path.join(__dirname, '../..');
const dojoDir = path.join(root, 'dojo_libs/dojo_11/dojo/dojo');
const sourceDir = process.env.GNR_JS_SOURCE || path.join(__dirname, '../gnr_d11/js');

// the real dojo.date.locale: patch_parse reads the match groups of the regexp
// it builds from the date and time patterns
function createContext() {
    const context = {console, File: function() {}, gnr: {}, genro: {}, setTimeout};
    vm.createContext(context);
    const run = (dir, filename) => vm.runInContext(readFileSync(path.join(dir, filename), 'utf8'), context, {filename});
    run(path.join(dojoDir, '_base/_loader'), 'bootstrap.js');
    const dojo = context.dojo;
    Object.assign(dojo, {_hasResource: {}, provide: name => dojo.getObject(name, true), require() {},
                         requireLocalization() {}, deprecated() {}, isIE: 0, Deferred: function() {}, locale: 'en'});
    for (const filename of ['lang.js', 'array.js']) run(path.join(dojoDir, '_base'), filename);
    for (const filename of ['i18n.js', 'regexp.js', 'string.js', 'date.js']) run(dojoDir, filename);
    run(path.join(dojoDir, 'cldr'), 'supplemental.js');
    run(path.join(dojoDir, 'date'), 'locale.js');
    const gregorian = vm.runInContext(readFileSync(path.join(dojoDir, 'cldr/nls/gregorian.js'), 'utf8'), context);
    dojo._loadedModules = {'dojo.cldr.nls.gregorian': {ROOT: gregorian}};
    context.dijit = {form: {ValidationTextBox: function() {}, CheckBox: function() {}}};
    // genro_widgets.js extends dijit classes this harness does not load
    dojo.declare = function(name, base, members) {
        function Declared(...args) {
            if (base) base.apply(this, args);
            if (Object.hasOwn(members, 'constructor')) members.constructor.apply(this, args);
        }
        Declared.prototype = Object.assign(Object.create(base && base.prototype ? base.prototype : Object.prototype), members);
        Declared.prototype.constructor = Declared;
        return dojo.setObject(name, Declared);
    };
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js', 'genro_widgets.js']) run(sourceDir, filename);
    const data = new context.gnr.GnrBag();
    data.setBackRef();
    Object.assign(context.genro, {_data: data, getData: p => data.getItem(p),
                                  getDataNode: (p, autocreate) => data.getNode(p, false, autocreate)});
    const main = new context.gnr.GnrDomSource();
    context.genro.src = {_main: main, _index: {}, _started: true, formsToUpdate: {}};
    context.genro.wdg = {getHandler: () => null};
    return {context, main};
}

// what dijit does on blur: parse the displayed text with the widget constraints
function parseOnBlur(text, timePattern) {
    const {context, main} = createContext();
    main._('DatetimeTextBox', 'field', {tag: 'DatetimeTextBox', value: '^record.ts'});
    const handler = new context.gnr.widgets.DatetimeTextBox();
    const widget = {gnr: handler, sourceNode: main.getNode('field'), _focused: false};
    return handler.patch_parse.call(widget, text, {selector: 'datetime', datePattern: 'dd/MM/yy', timePattern});
}

function assertDateTime(result, [hours, minutes, seconds]) {
    assert.equal(Object.prototype.toString.call(result), '[object Date]');
    assert.ok(!isNaN(result.getTime()), 'Invalid Date');
    assert.deepEqual([result.getFullYear(), result.getMonth(), result.getDate()], [2025, 7, 6]);
    assert.deepEqual([result.getHours(), result.getMinutes(), result.getSeconds()], [hours, minutes, seconds]);
}

test('a typed 24h datetime is parsed to a valid date', () => {
    assertDateTime(parseOnBlur('06/08/25 14:30', 'HH:mm'), [14, 30, 0]);
});

test('a typed 24h datetime with seconds keeps its seconds', () => {
    assertDateTime(parseOnBlur('06/08/25 14:30:15', 'HH:mm:ss'), [14, 30, 15]);
});

test('a typed 12h datetime is still parsed with its day period', () => {
    assertDateTime(parseOnBlur('06/08/25 2:30 PM', 'h:mm a'), [14, 30, 0]);
});
