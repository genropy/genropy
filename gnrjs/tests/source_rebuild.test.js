const assert = require('node:assert/strict');
const {test} = require('node:test');
const {loadClasses} = require('./bag_audit_harness.cjs');

for (const mode of ['legacy', 'genro-bag-js-mixin']) {
    test(`${mode}: unfreezing dialog content requests a rebuild without replacing it`, () => {
        const previous = process.env.GNR_JS_BAG;
        let context;
        try {
            process.env.GNR_JS_BAG = mode;
            context = loadClasses(['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js', 'genro_src.js']);
        } finally {
            if (previous === undefined) delete process.env.GNR_JS_BAG;
            else process.env.GNR_JS_BAG = previous;
        }
        const {gnr, genro} = context;
        const handler = genro.src = new gnr.GnrSrcHandler({});
        handler._trigger_ins = () => {};
        const updates = [];
        handler._trigger_upd = event => updates.push(event);
        const content = new gnr.GnrDomSource();
        const wrapper = handler._main.setItem('prompt', content, {tag: 'div'});
        const bagUpdates = [];
        handler._main.subscribe('rebuild-observer', {upd: event => bagUpdates.push(event)});
        wrapper.freeze();
        const dialog = content.setItem('dialog', new gnr.GnrDomSource(), {tag: 'dialog'});
        assert.equal(updates.length, 0);
        wrapper.unfreeze();
        assert.equal(updates.length, 1);
        assert.equal(bagUpdates.length, mode === 'legacy' ? 1 : 0);
        if (mode === 'legacy') {
            assert.equal(bagUpdates[0].node, wrapper);
            assert.equal(bagUpdates[0].oldvalue, content);
        }
        assert.equal(updates[0].node, wrapper);
        assert.equal(updates[0].oldvalue, content);
        assert.equal(wrapper.getValue(), content);
        assert.equal(dialog.getParentNode(), wrapper);
        wrapper.unfreeze(true);
        assert.equal(updates.length, 1);
        wrapper.freeze();
        wrapper.rebuild();
        assert.equal(updates.length, 1, 'frozen source must still suppress rebuilds');
    });
}
