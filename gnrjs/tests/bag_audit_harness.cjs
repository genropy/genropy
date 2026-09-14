const {readFileSync} = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

class Deferred {
    constructor() {
        this.callbacks = [];
    }

    addCallback(callback) {
        this.callbacks.push(callback);
        return this;
    }

    callback(value) {
        return this.callbacks.reduce((result, callback) => callback(result), value);
    }

    cancel() {}
}

function loadClasses(filenames = ['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js'], withNamespace = true) {
    const context = {
        alert() {},
        console,
        TextEncoder, TextDecoder, Uint8Array,
        atob, btoa,
        dijit: {},
        document: {},
        File: function() {},
        genro: {isMobile: false, time36Id: () => 'generated'},
        setTimeout,
        window: {}
    };
    if (withNamespace) context.gnr = {};
    context.dojo = {
        Deferred,
        _hasResource: {},
        version: {major: 1, minor: 1},
        require() {},
        eval,
        hitch: (object, method) => method === undefined ? object :
            (typeof method === 'string' ? object[method] : method).bind(object),
        forEach: (items, callback) => Array.prototype.forEach.call(items || [], callback),
        some: (items, callback) => Array.prototype.some.call(items || [], callback),
        toJson: JSON.stringify,
        provide() {},
        extend(constructor, members) { Object.assign(constructor.prototype, members); },
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
    vm.runInContext(readFileSync(path.join(__dirname,
        '../../dojo_libs/dojo_11/dojo_release/dojo/_base/Deferred.js'), 'utf8'), context,
    {filename: 'dojo/_base/Deferred.js'});
    const sourceDir = process.env.GNR_JS_SOURCE || path.join(__dirname, '../gnr_d11/js');
    for (const requested of filenames) {
        const selected = requested === 'gnrbag.js' && process.env.GNR_JS_BAG === 'genro-bag-js'
            ? ['genro_bagjs_bundle.js', 'gnrbag_genro.js'] : [requested];
        for (const filename of selected) {
            vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
        }
    }
    return context;
}



module.exports = {loadClasses};

function loadPair() {
 const previous = process.env.GNR_JS_BAG;
 try { delete process.env.GNR_JS_BAG; const legacy = loadClasses(); process.env.GNR_JS_BAG = 'genro-bag-js'; return {legacy, selected: loadClasses()}; }
 finally { if (previous === undefined) delete process.env.GNR_JS_BAG; else process.env.GNR_JS_BAG = previous; }
}
module.exports.loadPair = loadPair;
