const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

function createSrc() {
    //timers run when the test asks: an error rethrown in one is collected there
    const timers = [];
    const context = {console, gnr: {}, genro: {}, setTimeout: cb => timers.push(cb)};
    const uncaught = () => timers.splice(0).flatMap(cb => {
        try {
            cb();
            return [];
        } catch (e) {
            return [e];
        }
    });
    context.dojo = {
        Deferred: function() {},
        hitch: (object, method) => (typeof method === 'string' ? object[method] : method).bind(object),
        forEach: (items, callback) => Array.prototype.forEach.call(items || [], callback),
        some: (items, callback) => Array.prototype.some.call(items || [], callback),
        subscribe: () => ({}),
        unsubscribe: () => {},
        publish: () => {},
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
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js', 'genro_src.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    const genro = context.genro;
    genro.isDeveloper = false;
    genro.wdg = {getHandler: () => null};
    genro._data = new context.gnr.GnrBag();
    genro.src = new context.gnr.GnrSrcHandler({});
    //a pane already on screen, inserted silently as there is no DOM to build into
    const pane = genro.src._main._('div', 'pane', {}, {doTrigger: false});
    pane.getParentNode().domNode = {};
    //buildNode builds the node with the content it has at that moment, and
    //fails as makeDomNode does when there is no destination
    const built = [];
    genro.src.buildNode = (node, where) => {
        if (!where) {
            throw new TypeError("Cannot read properties of undefined (reading 'containerNode')");
        }
        const mark = n => {
            n.domNode = {};
            built.push(n.label);
            const content = n.getValue('static');
            if (content instanceof context.gnr.GnrBag) {
                content.forEach(mark, 'static');
            }
        };
        mark(node);
        const onBuild = node.attr.onBuild;
        if (onBuild) {
            onBuild(node);
        }
    };
    return {genro, pane, built, timers, uncaught};
}

//what makeHiderLayer does from inside a running build: the layer, then its message
function addHider(pane) {
    const hider = pane._('div', 'hiderNode', {});
    hider._('div', 'message', {});
    return hider.getParentNode();
}

test('a parent and its child queued during a build are built together', t => {
    const {genro, pane, built, uncaught} = createSrc();
    const errors = [];
    t.mock.method(console, 'error', (...args) => errors.push(args));
    pane._('div', 'host', {onBuild: () => addHider(pane)});
    assert.deepEqual(uncaught(), []);
    assert.deepEqual(errors, []);
    assert.deepEqual(built, ['host', 'hiderNode', 'message']);
    assert.equal(genro.src.building, false);
    assert.equal(genro.src.pendingBuild.length, 0);
});

test('a deeper queued insert waits for its queued ancestor', () => {
    const {genro, pane, built, uncaught} = createSrc();
    pane._('div', 'host', {onBuild: () => {
        const hider = addHider(pane);
        hider.getValue().getItem('message')._('div', 'spinner', {});
    }});
    assert.deepEqual(uncaught(), []);
    assert.deepEqual(built, ['host', 'hiderNode', 'message', 'spinner']);
    assert.equal(genro.src.building, false);
});

test('a node changed while its insertion is queued is built once, with its last state', () => {
    const {genro, pane, built, uncaught} = createSrc();
    let hider;
    pane._('div', 'host', {onBuild: () => {
        hider = addHider(pane);
        hider.setAttr({_class: 'hiderLayer hiderLocked'});
    }});
    assert.deepEqual(uncaught(), []);
    assert.deepEqual(built, ['host', 'hiderNode', 'message']);
    assert.equal(hider.attr._class, 'hiderLayer hiderLocked');
    assert.equal(genro.src.building, false);
});

test('a failed build does not stop the queue nor leave building set', () => {
    const {genro, pane, built, timers, uncaught} = createSrc();
    const buildNode = genro.src.buildNode;
    genro.src.buildNode = (node, where) => {
        if (node.label == 'broken') {
            throw new Error('broken build');
        }
        return buildNode(node, where);
    };
    pane._('div', 'host', {onBuild: () => {
        pane._('div', 'broken', {});
        pane._('div', 'sibling', {});
    }});
    //the caller goes on, the error is raised again on its own, uncaught
    assert.deepEqual(built, ['host', 'sibling']);
    assert.equal(genro.src.building, false);
    assert.equal(timers.length, 1);
    assert.deepEqual(uncaught().map(e => e.message), ['broken build']);
    pane._('div', 'later', {});
    assert.deepEqual(built, ['host', 'sibling', 'later']);
});

test('a node whose build throws is not left building', () => {
    const {pane} = createSrc();
    const node = pane._('div', 'failing', {}, {doTrigger: false}).getParentNode();
    node._doBuildNode = () => {
        throw new Error('widget creation failed');
    };
    assert.throws(() => node.build({}), /widget creation failed/);
    assert.equal(node._isBuilding, false);
});
