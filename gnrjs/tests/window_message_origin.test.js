const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

const ORIGIN = 'https://app.example.com';

function createPage() {
    const listeners = [];
    const context = {
        console, gnr: {}, dijit: {}, document: {}, navigator: {},
        window: {location: {origin: ORIGIN}, addEventListener: (name, cb) => listeners.push(cb)}
    };
    context.dojo = {
        version: {major: 1, minor: 1},
        require: () => {},
        declare(name, base, members) {
            function Declared() {}
            Declared.prototype = Object.assign(Object.create(base ? base.prototype : Object.prototype), members);
            const names = name.split('.');
            let namespace = context;
            for (const part of names.slice(0, -1)) namespace = namespace[part] ||= {};
            namespace[names.at(-1)] = Declared;
            return Declared;
        }
    };
    vm.createContext(context);
    const sourceDir = process.env.GNR_JS_SOURCE || path.join(__dirname, '../gnr_d11/js');
    for (const filename of ['gnrlang.js', 'gnrbag.js', 'genro.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    const genro = Object.create(context.gnr.GenroClient.prototype);
    const published = [];
    genro.publish = (topic, kw) => published.push([typeof topic === 'object' ? topic.topic : topic, {...kw}]);
    context.genro = genro;
    genro.windowMessageListener();
    return {published, post: (data, origin) => listeners.forEach(cb => cb({data, origin}))};
}

test('a message of this origin is published whatever its topic', () => {
    const page = createPage();
    page.post({topic: 'th_external_query', table: 'invc.invoice'}, ORIGIN);
    page.post({topic: 'selectIframePage', openKw: {topic: 'th_external_query'}}, ORIGIN);
    page.post({topic: 'externalSetData', path: 'a.b', value: 1}, ORIGIN);
    assert.deepEqual(page.published, [
        ['th_external_query', {table: 'invc.invoice'}],
        ['selectIframePage', {openKw: {topic: 'th_external_query'}}],
        ['externalSetData', {path: 'a.b', value: 1}]]);
});

test('another origin does not reach the topics that load data or structs', () => {
    const page = createPage();
    for (const topic of ['th_external_query', 'selectIframePage', 'externalSetData']) {
        page.post({topic, view: {struct_xml: '<x/>'}}, 'https://other.example.com');
        page.post({topic: {topic, iframe: '*'}, view: {struct_xml: '<x/>'}}, 'https://other.example.com');
    }
    assert.deepEqual(page.published, []);
});

test('another origin still reaches the other topics', () => {
    const page = createPage();
    page.post({topic: 'setClientWidth', width: 300}, 'https://other.example.com');
    page.post({msg: 'externalFrameComplete'}, 'https://other.example.com');
    assert.deepEqual(page.published, [
        ['setClientWidth', {width: 300}],
        ['windowMessage', {msg: 'externalFrameComplete'}]]);
});
