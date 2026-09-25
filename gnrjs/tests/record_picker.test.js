const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

function runtime() {
    const context = {console, TextEncoder, TextDecoder, Uint8Array, File, Blob, atob, btoa, gnr:{}, genro:{}, clearTimeout, setTimeout};
    context.dojo = {
        Deferred: class Deferred {},
        eval,
        hitch:(object, method) => (typeof method === 'string' ? object[method] : method).bind(object),
        forEach:(items, callback) => Array.prototype.forEach.call(items || [], callback),
        some:(items, callback) => Array.prototype.some.call(items || [], callback),
        declare(name, base, members) {
            function Declared(...args) {
                if (base) base.apply(this, args);
                if (Object.hasOwn(members, 'constructor')) members.constructor.apply(this, args);
            }
            Declared.prototype = Object.assign(Object.create(base ? base.prototype : Object.prototype), members);
            let namespace = context;
            const names = name.split('.');
            for (const part of names.slice(0, -1)) namespace = namespace[part] ||= {};
            namespace[names.at(-1)] = Declared;
        }
    };
    vm.createContext(context);
    for (const file of ['gnrjs/gnr_d11/js/gnrlang.js', 'gnrjs/gnr_d11/js/gnrbag.js',
        'resources/common/gnrcomponents/recordpicker/recordpicker.js']) {
        vm.runInContext(readFileSync(path.join(__dirname, '../..', file), 'utf8'), context, {filename:file});
    }
    return context;
}

test('multiple selection respects limits and updates immediately', () => {
    const {gnr} = runtime();
    const selection = new gnr.RecordPickerSelection(true, 2);
    selection.setValue('b');
    selection.toggle('a', true);
    selection.toggle('c', true);
    assert.equal(selection.value(), 'b,a');
    selection.toggle('b', false);
    selection.toggle('c', true);
    assert.equal(selection.value(), 'a,c');
});

test('single selection replaces the checked key and supports zero-valued identifiers', () => {
    const {gnr} = runtime();
    const selection = new gnr.RecordPickerSelection(false);
    selection.setValue(0);
    assert.equal(selection.value(), '0');
    selection.toggle('x', true);
    assert.equal(selection.value(), 'x');
    selection.toggle('x', false);
    assert.equal(selection.value(), null);
});

function localPicker() {
    const {gnr} = runtime();
    const picker = Object.create(gnr.RecordPicker.prototype);
    Object.assign(picker, {config:{identifier:'_pkey', captionField:'caption', checkedId:'^.checked', multiSelect:true,
        columns:'caption,city'}, query:'', revision:0, render() {}, writes:{}});
    picker.sourceNode = {setRelativeData(key, value) {picker.writes[key] = value;}};
    picker.selection = new gnr.RecordPickerSelection(true);
    const store = new gnr.GnrBag();
    store.setItem('a', null, {_pkey:'a', caption:'Rossi', city:'Milan'});
    store.setItem('b', new gnr.GnrBag({caption:'Rossi', city:'Bergamo'}), {_pkey:'b'});
    store.setItem('c', null, {_pkey:'c', caption:'Caffè Verde', city:'Turin'});
    picker.setStore(store);
    return picker;
}

test('empty search shows nothing; typing hides non-matches across fields and accents', () => {
    const picker = localPicker();
    assert.deepEqual(Array.from(picker.candidates), []);
    picker.query = 'rossi bergamo'; picker.search();
    assert.deepEqual(Array.from(picker.candidates), ['b']);
    picker.query = 'caffe'; picker.search();
    assert.deepEqual(Array.from(picker.candidates), ['c']);
});

test('filtering and empty results preserve checked records and their captions', () => {
    const picker = localPicker();
    picker.selection.toggle('b', true);
    picker.query = 'Turin'; picker.search();
    assert.deepEqual(Array.from(picker.candidates), ['c']);
    assert.equal(picker.selection.value(), 'b');
    assert.equal(picker.caption('b'), 'Rossi');
    picker.query = 'not found'; picker.search();
    assert.equal(picker.candidates.length, 0);
    assert.equal(picker.selection.value(), 'b');
});

test('external store replacement makes deleted selections unavailable', () => {
    const picker = localPicker();
    picker.selection.setValue('a');
    picker.setStore(null);
    assert.equal(picker.selection.value(), 'a');
    assert.equal(!!picker.available('a'), false);
});

test('out-of-order remote results cannot overwrite a more recent search', () => {
    const {gnr} = runtime();
    const picker = Object.create(gnr.RecordPicker.prototype);
    const pending = [];
    Object.assign(picker, {config:{table:'pkg.table', limit:2},
        ready:true, records:new Map(), localKeys:[], revision:0, selection:new gnr.RecordPickerSelection(true),
        render() {}, renderStatus() {}, request(params, success, failure) {pending.push({params, success, failure});}});
    picker.query = 'old'; picker.search();
    picker.query = 'new'; picker.search();
    const result = key => {const bag = new gnr.GnrBag(); bag.setItem(key, null, {_pkey:key, caption:key}); return bag;};
    pending[1].success(result('new'));
    pending[0].success(result('old'));
    assert.deepEqual(Array.from(picker.candidates), ['new']);
    pending[0].failure();
    assert.equal(picker.error, false);
});

test('RPC transport unwraps the BagNode returned with selection metadata', () => {
    const {gnr, genro} = runtime();
    const picker = Object.create(gnr.RecordPicker.prototype);
    Object.assign(picker, {config:{table:'pkg.table', limit:2}, queryParams:{}, sourceNode:{}});
    const bag = new gnr.GnrBag();
    bag.setItem('a', null, {_pkey:'a', caption:'Customer A'});
    const envelope = new gnr.GnrBag();
    const node = envelope.setItem('result', bag, {columns:'caption'});
    genro.rpc = {remoteCall(method, params, mode, httpMethod, preventCache, callback) {
        assert.equal(method, 'app.dbSelect');
        assert.equal(params.limit, 3);
        callback(node);
        return {addErrback() {}};
    }};
    let received;
    picker.request({_querystring:'*'}, result => {received = result;}, () => assert.fail('Unexpected RPC failure'));
    assert.equal(received, bag);
});

test('clearing a remote search empties candidates, retains checked rows and ignores pending responses', () => {
    const {gnr} = runtime();
    const picker = Object.create(gnr.RecordPicker.prototype);
    const pending = [];
    Object.assign(picker, {config:{table:'pkg.table', limit:2, captionField:'caption'},
        ready:true, records:new Map([['a', {_pkey:'a', caption:'A'}]]),
        query:'', revision:0, generation:0, selection:new gnr.RecordPickerSelection(true),
        render() {}, renderStatus() {}, request(params, success) {pending.push({params, success});}});
    picker.reload();
    assert.equal(pending.length, 0);
    picker.records.set('a', {_pkey:'a', caption:'A'});
    picker.selection.setValue('a');
    picker.query = 'B'; picker.search();
    picker.query = ''; picker.search();
    const bag = new gnr.GnrBag(); bag.setItem('b', null, {_pkey:'b', caption:'B'});
    pending[0].success(bag);
    assert.deepEqual(Array.from(picker.candidates), []);
    assert.equal(pending.length, 1);
    assert.equal(picker.caption('a'), 'A');
    assert.equal(picker.selection.value(), 'a');
});

test('hydration responses for obsolete external values are ignored', () => {
    const {gnr} = runtime();
    const picker = Object.create(gnr.RecordPicker.prototype);
    const pending = [];
    Object.assign(picker, {config:{table:'pkg.table'}, records:new Map(), generation:1,
        selection:new gnr.RecordPickerSelection(true), queryParams:{condition:'$active IS TRUE'},
        render() {}, request(params, success, failure) {pending.push({params, success, failure});}});
    picker.selection.setValue('a'); picker.hydrate();
    picker.selection.setValue('b'); picker.hydrate();
    assert.equal(pending[1].params.condition, '($active IS TRUE) AND $pkey IN :_picker_keys');
    const rows = new gnr.GnrBag(); rows.setItem('b', null, {_pkey:'b', caption:'B'});
    pending[1].success(rows);
    pending[0].failure();
    assert.equal(picker.hydrating, false);
    assert.equal(picker.error, undefined);
    assert.equal(picker.available('b'), true);
});

test('click updates checkedId and output Bags immediately and previews the latest checked record', () => {
    const picker = localPicker();
    picker.config.selectedRecord = '^.records';
    picker.config.selectedCaption = '^.caption';
    picker.select('a', true);
    assert.equal(picker.writes['.checked'], 'a');
    picker.select('b', true);
    assert.equal(picker.writes['.checked'], 'a,b');
    assert.equal(picker.writes['.records'].len(), 2);
    assert.equal(picker.writes['.caption'], 'Rossi, Rossi');
    assert.equal(picker.peek, 'b');
    picker.select('a', false);
    assert.equal(picker.peek, 'b');
    picker.select('c', true);
    assert.equal(picker.peek, 'c');
    picker.select('c', false);
    assert.equal(picker.peek, 'b');
    picker.select('b', false);
    assert.equal(picker.peek, undefined);
    assert.equal(picker.writes['.checked'], '');
    assert.equal(picker.confirm, undefined);
    assert.equal(picker.cancel, undefined);
});

test('single mode replaces the selection, updates preview, and respects disabled state', () => {
    const picker = localPicker();
    picker.selection.multiple = false;
    picker.config.multiSelect = false;
    picker.config.selectedRecord = '^.record';
    picker.select('a', true);
    picker.select('b', true);
    assert.equal(picker.writes['.checked'], 'b');
    assert.equal(picker.writes['.record'].getItem('city'), 'Bergamo');
    assert.equal(picker.peek, 'b');
    picker.disabled = true;
    picker.select('a', true);
    assert.equal(picker.writes['.checked'], 'b');
});
