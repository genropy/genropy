const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

// The close icon of a form dialog publishes 'close', which dismisses the form.
// dijit writes the value of a blurred field only when its focus manager catches up:
// a field still focused when the icon is clicked lost its edit, and the late value
// left the dismissed form changed with no record. The value is committed first.
const WIDGETS_JS = path.join(__dirname, '../gnr_d11/js/genro_widgets.js');

function onCancelPublish() {
    const source = readFileSync(WIDGETS_JS, 'utf8');
    const start = source.indexOf('attributes_mixin_onCancelPublish:function');
    assert.ok(start > 0, 'onCancelPublish is defined in genro_widgets.js');
    const body = source.slice(source.indexOf('function', start), source.indexOf('\n    },', start) + 6);
    return body;
}

function run(focused) {
    const calls = [];
    const context = {
        genro: {activeForm: focused ? {currentFocused: focused} : null,
                dom: {getEventModifiers: () => null}},
    };
    vm.createContext(context);
    const fn = vm.runInContext('(' + onCancelPublish() + ')', context);
    const dialog = {sourceNode: {publish: (topic) => calls.push('publish:' + topic)}};
    if (focused) {
        focused.calls = calls;
    }
    fn.call(dialog, {});
    return {calls, context};
}

function field(isFocused) {
    const f = {
        _focused: isFocused,
        _setBlurValue() { this.calls.push('commit'); },
        focusNode: {blur: () => f.calls.push('blur')},
    };
    return f;
}

test('a focused field writes its value before the dialog closes', () => {
    const {calls, context} = run(field(true));
    assert.deepEqual(calls, ['commit', 'blur', 'publish:close']);
    assert.equal(context.genro.activeForm.currentFocused, null);
});

test('a field that already lost the focus is not committed again', () => {
    const {calls} = run(field(false));
    assert.deepEqual(calls, ['blur', 'publish:close']);
});

test('without a focused field the dialog just closes', () => {
    const {calls} = run(null);
    assert.deepEqual(calls, ['publish:close']);
});
