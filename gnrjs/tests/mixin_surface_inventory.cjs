const {loadClasses} = require('./bag_audit_harness.cjs');
const legacy = loadClasses(['gnrlang.js','gnrbag.js','gnrdomsource.js']);
const current = loadClasses(['gnrlang.js','genro_bagjs_bundle.js','gnrbag_mixin.js','gnrdomsource.js']);
const names = ['GnrBag','GnrBagNode','GnrBagResolver','GnrBagCbResolver','GnrBagFormula','GnrBagGetter','GnrDomSource','GnrDomSourceNode'];
function methods(proto) {
    const found = new Set();
    for (; proto && Object.getPrototypeOf(proto); proto = Object.getPrototypeOf(proto)) {
        for (const [key, descriptor] of Object.entries(Object.getOwnPropertyDescriptors(proto))) {
            if (key !== 'constructor' && typeof descriptor.value === 'function') found.add(key);
        }
    }
    return found;
}
console.log('# Missing methods in the lightweight GenroJS mixin\n');
console.log('Generated from runtime prototypes, including inherited methods. Presence does not prove signature or behavioral compatibility. Missing methods are candidates for review, not automatic additions.\n');
for (const name of names) {
    console.log('## ' + name + '\n');
    if (!current.gnr[name]) { console.log('Class absent.\n'); continue; }
    const available = methods(current.gnr[name].prototype);
    const missing = [...methods(legacy.gnr[name].prototype)].filter(key => !available.has(key)).sort();
    console.log(missing.length ? missing.map(key => '- `' + key + '`').join('\n') + '\n' : 'No missing methods.\n');
}
