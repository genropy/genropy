const assert = require('node:assert/strict');
const {test} = require('node:test');
const {loadPair} = require('./bag_audit_harness.cjs');

for (const mode of ['legacy', 'selected', 'standalone']) {
    test(`widget restores the full original attributes with ${mode} setAttr`, () => {
        const pair = loadPair();
        const context = mode === 'legacy' ? pair.legacy : pair.selected;
        const Bag = mode === 'standalone' ? context.GenroBagJS.Bag : context.gnr.GnrBag;
        const bag = new Bag();
        (bag.setBackRef || bag.setBackref).call(bag);
        bag.setItem('widget', null, {tag:'input',disabled:false});
        const node = bag.getNode('widget');
        node.attr.command = null;
        node._original_attributes = {...node.attr};
        node.attr.disabled = true;
        node.attr.temporaryModifier = 'active';
        const notifications=[];
        bag.subscribe('audit',{any:event=>notifications.push(event)});
        let disabled;
        node.getAttributeFromDatasource = name=>node.attr[name];
        node.setDisabled = value=>{disabled=value;};

        context.gnr.GnrDomSourceNode.prototype.doUpdateAttrBuiltObj.call(
            node,'disabled',{evt:'upd'},'node');

        assert.equal(node.attr.temporaryModifier, undefined);
        assert.equal(node.attr.disabled, false);
        assert.equal(Object.hasOwn(node.attr,'command'), true);
        assert.equal(node.attr.command, null);
        assert.equal(node._original_attributes, null);
        assert.equal(disabled, false);
        assert.equal(notifications.length, 1);
    });
}
