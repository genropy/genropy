const assert = require('node:assert/strict');
const {test} = require('node:test');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {loadClasses} = require('./bag_audit_harness.cjs');
for (const mode of ['legacy','mixin']) {
    test(`${mode}: expired is a boolean getter with cache/reset semantics`, () => {
        const previous = process.env.GNR_JS_BAG;
        delete process.env.GNR_JS_BAG;
        let c;
        try { c = loadClasses(mode === 'legacy' ? ['gnrlang.js','gnrbag.js'] :
            ['gnrlang.js','genro_bagjs_bundle.js','gnrbag_mixin.js']); } finally {
            if (previous !== undefined) process.env.GNR_JS_BAG = previous;
        }
        const r = new c.gnr.GnrBagResolver({}, false, -1);
        const stamp = value => {if (mode === 'legacy') r.lastUpdate = value; else r._lastUpdate = value;};
        assert.equal(r.expired, true);
        stamp(Date.now());
        assert.equal(r.expired, false);
        r.reset();
        assert.equal(r.expired, true);
        r.setCacheTime(60);
        stamp(Date.now());
        assert.equal(r.expired, false);
        stamp(Date.now()-61000);
        assert.equal(r.expired, true);
        r.setCacheTime(0);
        assert.equal(r.expired, true);
    });
}
test('GenroJS callers use property syntax', () => {
    for (const name of ['gnrbag.js','genro_tree.js','genro_wdg.js','genro_widgets.js','genro_patch.js']) {
        const source=readFileSync(path.join(__dirname,'../gnr_d11/js',name),'utf8');
        assert.doesNotMatch(source,/\.expired\s*\(/,name);
    }
});
