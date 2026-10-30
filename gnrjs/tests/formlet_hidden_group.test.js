const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

const sourceDir = () => process.env.GNR_JS_SOURCE || path.join(__dirname, '../gnr_d11/js');

function loadContext() {
    const context = {console, File: function() {}, gnr: {}, genro: {}};
    context.dojo = {
        Deferred: function() {},
        eval,
        hitch: (object, method) => (typeof method === 'string' ? object[method] : method).bind(object),
        forEach: (items, callback) => Array.prototype.forEach.call(items || [], callback),
        some: (items, callback) => Array.prototype.some.call(items || [], callback),
        toJson: JSON.stringify,
        require() {},
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
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir(), filename), 'utf8'), context, {filename});
    }
    return context;
}

const context = loadContext();

// A formlet has no table cells to collect: setHidden on a hiddenGroup member
// reaches the siblings with the same hiddenGroup and hides their labledbox.
function formletGroup() {
    const calls = [];
    const siblings = Object.create(context.gnr.GnrDomSource.prototype);
    const container = {getValue: () => siblings};
    function wrapper(label, attr) {
        return {label, domNode: {}, _contentNode: {attr},
                getParentNode: () => container,
                setHidden: (hidden, fromGroup) => calls.push([label, hidden, fromGroup])};
    }
    const leaderWrapper = wrapper('alfa', {hiddenGroup: 'g'});
    const nodes = [leaderWrapper, wrapper('beta', {}), wrapper('gamma', {hiddenGroup: 'g'}),
                   wrapper('other', {hiddenGroup: 'h'}),
                   {label: 'unbuilt', _contentNode: {attr: {hiddenGroup: 'g'}},
                    setHidden: () => calls.push(['unbuilt'])}];
    siblings.getNodes = () => nodes;
    const leader = Object.create(context.gnr.GnrDomSourceNode.prototype);
    leader.attr = {hiddenGroup: 'g'};
    return {leader, leaderWrapper, calls};
}

test('a formlet hiddenGroup hides the sibling cells of its group only', () => {
    const {leader, leaderWrapper, calls} = formletGroup();
    leader._setHiddenGroup(true, leaderWrapper);
    assert.deepEqual(calls, [['gamma', true, true]]);
});

test('showing the leader shows its group again', () => {
    const {leader, leaderWrapper, calls} = formletGroup();
    leader._setHiddenGroup(false, leaderWrapper);
    assert.deepEqual(calls, [['gamma', false, true]]);
});

// A plain HTML member gets no widget setHidden: built hidden, it must still
// reach sourceNode.setHidden once the build ends, or its group stays visible.
test('a plain HTML node built hidden hides its group after the build', () => {
    vm.runInContext(readFileSync(path.join(sourceDir(), 'genro_wdg.js'), 'utf8'), context, {filename: 'genro_wdg.js'});
    const afterBuild = [];
    context.genro.src = {onBuiltCall: cb => afterBuild.push(cb)};
    context.genro.dom = {getStyleDict: () => ({})};
    context.genro.assert = () => {};
    const wdg = Object.create(context.gnr.GnrWdgHandler.prototype);
    wdg.noConvertStyle = {};
    wdg.getHandler = () => ({_creating: () => ({}), _created() {}});
    wdg.makeDomNode = () => ({});
    wdg.createHtmlElement = () => ({});
    wdg.linkSourceNode = () => {};
    const hidden = [];
    const sourceNode = {setHidden: value => hidden.push(value)};
    wdg.create('div', {}, {hidden: true, hiddenGroup: 'g'}, -1, sourceNode);
    assert.deepEqual(hidden, []);
    afterBuild.forEach(cb => cb());
    assert.deepEqual(hidden, [true]);
});
