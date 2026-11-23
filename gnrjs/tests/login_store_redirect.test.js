const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

const source = file => fs.readFileSync(path.resolve(__dirname, file), 'utf8');
const client = source('../gnr_d11/js/genro.js');
const login = source('../../projects/gnrcore/packages/adm/resources/login.js');

function confirmLogin({pathname = '/', store = 'demo', base = '/', home = base,
                       rootpage, envRootpage}) {
    const location = new URL(pathname, 'https://example.test');
    const navigation = [];
    location.assign = target => {
        const url = new URL(target, location);
        assert.equal(url.origin, location.origin);
        navigation.push(url.pathname + url.search + url.hash);
    };
    const data = {'gnr.defaultUrl': base, 'gnr.homeUrl': home};
    const avatar = {getItem: key => key === 'user' ? 'tester' : null};
    const form = {
        getRelativeData: key => key === 'gnr.rootenv.rootpage' ? envRootpage : avatar,
        getValue: () => ({walk() {}})
    };
    const context = vm.createContext({
        URL, window: {location}, dijit: {}, gnr: {GnrBag: Object},
        objectPop: (obj, key) => delete obj[key],
        dojo: {require() {}, version: {major: 1, minor: 1}, declare(name, parent, methods) {
            if (name === 'gnr.GenroClient') {
                context.genro = Object.create(methods);
            }
        }}
    });
    vm.runInContext(client, context);
    Object.assign(context.genro, {
        lockScreen() {},
        getData: key => key === 'gnr.avatar.user_record.dbstore'
            ? data['gnr.avatar'].user_record.dbstore : data[key],
        setData: (key, value) => { data[key] = value; },
        serverCall: (method, params, callback) => callback({user_record: {dbstore: store}, rootpage}),
        pageReload: () => navigation.push('reload')
    });
    const component = vm.runInContext(login + '\nLoginComponent', context);
    component.confirmAvatar(form, 'login_doLogin', {hide() {}}, true, 'Invalid login', false);
    return navigation;
}

test('a store user at the site root lands in their store', () => {
    assert.deepEqual(confirmLogin({}), ['/demo/']);
    assert.deepEqual(confirmLogin({pathname: '/erp/', base: '/erp/'}), ['/erp/demo/']);
});

test('the store redirect uses the login rootpage or the rootenv fallback', () => {
    assert.deepEqual(confirmLogin({rootpage: '/reports?year=2026', envRootpage: '/other'}),
                     ['/demo/reports?year=2026']);
    assert.deepEqual(confirmLogin({envRootpage: 'reports'}), ['/demo/reports']);
});

test('store names must match a whole segment below the mount point', () => {
    const base = '/erp/';
    assert.deepEqual(confirmLogin({base, pathname: '/erp/demo2/', home: '/erp/demo2/'}), ['/erp/demo/']);
    for (const pathname of ['/erp/demo', '/erp/demo/', '/erp/demo/index']) {
        assert.deepEqual(confirmLogin({base, pathname, home: '/erp/demo/'}), ['reload']);
    }
});

test('regular navigation still handles a user already in their store or without an assigned store', () => {
    assert.deepEqual(confirmLogin({pathname: '/demo/', home: '/demo/', rootpage: '/reports'}),
                     ['/demo/reports']);
    assert.deepEqual(confirmLogin({store: null}), ['reload']);
    assert.deepEqual(confirmLogin({store: null, rootpage: '/reports'}), ['/reports']);
});
