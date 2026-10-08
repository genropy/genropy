const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {test} = require('node:test');
const vm = require('node:vm');
const path = require('node:path');

function createPane(childCount) {
    const root = process.env.GNR_ROOT || path.join(__dirname, '../..');
    const context = {gnr: {}, genro: {}, dijit: {_Widget: function() {}, layout: {}}, console};
    context.dojo = {
        _hasResource: {}, provide() {}, require() {}, requireLocalization() {},
        declare(name, base, members) {
            function Declared() {}
            Declared.prototype = members;
            const parts = name.split('.');
            let target = context;
            for (const part of parts.slice(0, -1)) target = target[part] ||= {};
            target[parts.at(-1)] = Declared;
        },
        query(selector, node) {
            const children = [...node.children];
            children.filter = () => children;
            return children;
        },
        marginBox(node) { assert.ok(node, 'resize must not reach a destroyed widget'); return {}; },
        mixin: Object.assign
    };
    context.dijit.byNode = node => node.widget;
    context.dijit.layout.marginBox2contentBox = () => ({});
    vm.createContext(context);
    for (const file of ['gnrjs/gnr_d11/js/genro_src.js', 'dojo_libs/dojo_11/dojo_src/dijit/layout/ContentPane.js']) {
        vm.runInContext(readFileSync(path.join(root, file), 'utf8'), context, {filename: file});
    }
    const pane = Object.create(context.dijit.layout.ContentPane.prototype);
    pane.domNode = {children: []};
    const src = Object.create(context.gnr.GnrSrcHandler.prototype);
    Object.assign(src, {
        cleanupNodeSubscriptions() {}, _onDeletingContent() {}, deleteChildrenExternalWidget() {}
    });
    for (let i = 0; i < childCount; i++) {
        const node = {_onDeleting() {}};
        const widget = Object.create(context.dijit.layout.ContentPane.prototype);
        Object.assign(widget, {
            sourceNode: node, domNode: {children: []}, containerNode: {},
            getParent: () => pane,
            destroyRecursive() {
                pane.domNode.children.splice(pane.domNode.children.indexOf(this.domNode), 1);
                delete this.domNode;
                delete this.containerNode;
            }
        });
        widget.domNode.widget = widget;
        node.widget = widget;
        pane.domNode.children.push(widget.domNode);
    }
    pane._checkIfSingleChild();
    return {pane, src};
}

test('removing the sole widget clears the ContentPane layout child before a later resize', () => {
    const {pane, src} = createPane(1);
    const child = pane._singleChild;
    src._trigger_del({node: child.sourceNode});
    assert.equal(child.domNode, undefined);
    assert.doesNotThrow(() => pane.resize({}));
    assert.equal(pane._singleChild, undefined);
});

test('removing one of two widgets promotes the remaining widget to layout child', () => {
    const {pane, src} = createPane(2);
    const first = pane.domNode.children[0].widget;
    const remaining = pane.domNode.children[1].widget;
    src._trigger_del({node: first.sourceNode});
    assert.equal(pane._singleChild, remaining);
    assert.doesNotThrow(() => pane.resize({}));
});
