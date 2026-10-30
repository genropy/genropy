const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

function createCapture(rejection) {
    const alerts = [];
    const context = {console: {log() {}}, gnr: {}};
    context.genro = {dlg: {alert: (msg, title) => alerts.push([msg, title])}};
    context.navigator = {mediaDevices: {getUserMedia: () => Promise.reject(rejection)}};
    context.dojo = {
        eval,
        toJson: JSON.stringify,
        hitch: (object, method) => (typeof method === 'string' ? object[method] : method).bind(object),
        forEach: (items, callback) => Array.prototype.forEach.call(items || [], callback),
        some: (items, callback) => Array.prototype.some.call(items || [], callback),
        declare(name, base, members) {
            const bases = [].concat(base || []);
            function Declared(...args) {
                for (const b of bases) b.apply(this, args);
                if (Object.hasOwn(members, 'constructor')) members.constructor.apply(this, args);
            }
            Declared.prototype = Object.assign(Object.create(bases.length ? bases[0].prototype : Object.prototype),
                                               ...bases.slice(1).map(b => b.prototype), members);
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
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'genro_widgets.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    const sourceNode = {attr: {}, getAttributeFromDatasource: () => null};
    const widget = new context.gnr.widgets.video();
    return {
        alerts,
        start: async (capture_kw) => {
            widget.startCapture(sourceNode, capture_kw);
            await new Promise(setImmediate);
        }
    };
}

function permissionDenied() {
    return Object.assign(new Error('Permission denied'), {name: 'NotAllowedError'});
}

test('a denied capture without onReject shows the alert naming the reason', async () => {
    const capture = createCapture(permissionDenied());
    await capture.start({video: true});
    assert.deepEqual(capture.alerts,
                     [['Not allowed video capture NotAllowedError: Permission denied', 'Error']]);
});

test('a denied capture with onReject hands it the error instead of alerting', async () => {
    const rejection = permissionDenied();
    const capture = createCapture(rejection);
    const received = [];
    await capture.start({video: true, onReject: function(err) { received.push(err); }});
    assert.deepEqual(received, [rejection]);
    assert.deepEqual(capture.alerts, []);
});
