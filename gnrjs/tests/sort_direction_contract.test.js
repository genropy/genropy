const assert = require('node:assert/strict');
const {test} = require('node:test');
const {loadClasses} = require('./bag_audit_harness.cjs');

for (const mode of ['legacy', 'mixin']) {
    test(`${mode}: sort direction ignores suffixes without changing case sensitivity`, () => {
        const previous = process.env.GNR_JS_BAG;
        delete process.env.GNR_JS_BAG;
        let context;
        try {
            context = loadClasses(mode === 'legacy' ? ['gnrlang.js', 'gnrbag.js'] :
                ['gnrlang.js', 'genro_bagjs_bundle.js', 'gnrbag_mixin.js']);
        } finally {
            if (previous !== undefined) process.env.GNR_JS_BAG = previous;
        }
        const warnings = [];
        context.console = {...console, warn: message => warnings.push(message)};
        for (const [direction, expected] of [
            ['a', ['a', 'B']], ['d', ['B', 'a']],
            ['A', ['B', 'a']], ['D', ['a', 'B']]
        ]) {
            for (const suffix of ['', '*', 'sc', 'd', '**']) {
                const bag = new context.gnr.GnrBag();
                bag.setItem('one', 'a');
                bag.setItem('two', 'B');
                bag.sort('#v: ' + direction + suffix + ' ');
                assert.deepEqual(Array.from(bag.getNodes(), n => n.getValue()), expected,
                    direction + suffix);
            }
        }
        assert.deepEqual(warnings, []);
    });
}
