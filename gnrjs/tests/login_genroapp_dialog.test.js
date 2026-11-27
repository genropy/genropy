const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

const login = fs.readFileSync(path.resolve(__dirname, '../../projects/gnrcore/packages/adm/resources/login.js'), 'utf8');

// The login component in a page of GenroApp. `events` records, in order, when the login dialog is hidden or
// shown again and when the login goes on.
function page({href = 'https://app.test/', answers}) {
    const events = [];
    const data = {};
    const context = vm.createContext({
        URL,
        _T: text => text.replace('!![en]', ''),
        window: {
            location: {href, origin: 'https://app.test'},
            history: {replaceState: (state, title, url) => { context.window.location.href = url; }},
            __TAURI__: {core: {invoke: async command => answers[command]}}
        },
        genro: {
            dom: {
                addClass: (node, cls) => events.push('hidden'),
                removeClass: (node, cls) => events.push('shown')
            },
            serverCall: (method, kwargs, callback) => callback(answers[method]),
            fireEvent: name => events.push(name),
            publish: (topic, kw) => events.push(topic)
        }
    });
    const component = vm.runInContext(login + '\nLoginComponent', context);
    const form = {setRelativeData: (key, value) => { data[key] = value; }};
    return {component, form, dialog: {domNode: {}}, events, data};
}

const answer = items => ({getItem: key => items[key]});

test('after a valid ticket the dialog is shown again before the login goes on', async () => {
    const {component, form, dialog, events, data} = page({
        href: 'https://app.test/?genroapp_ticket=abc',
        answers: {ticket_rpc: answer({user: 'mario'})}
    });
    await component.ticketLogin(form, dialog, 'ticket_rpc');
    assert.deepEqual(events, ['hidden', 'shown', 'do_login_check']);
    assert.equal(data['_login.user'], 'mario');
    assert.equal(data['_login.device_user'], 'mario');
});

test('an expired ticket shows the dialog with its message', async () => {
    const {component, form, dialog, events} = page({
        href: 'https://app.test/?genroapp_ticket=abc',
        answers: {ticket_rpc: null}
    });
    await component.ticketLogin(form, dialog, 'ticket_rpc');
    assert.deepEqual(events, ['hidden', 'shown', 'failed_login_msg']);
});

test('a page without a ticket leaves the dialog as it is', async () => {
    const {component, form, dialog, events} = page({answers: {}});
    await component.ticketLogin(form, dialog, 'ticket_rpc');
    assert.deepEqual(events, []);
});

for (const mode of ['signature', 'password']) {
    test(`after a device signature in mode ${mode} the dialog is shown again`, async () => {
        const {component, form, dialog, events} = page({answers: {
            challenge_rpc: 'q0',
            device_sign: {key_id: 'k', user: 'mario', signature: 's', connector_id: 'c'},
            login_rpc: answer({user: 'mario', mode})
        }});
        assert.equal(await component.deviceSign(form, dialog, 'https://app.test', 'challenge_rpc', 'login_rpc'), true);
        assert.deepEqual(events, mode === 'signature' ? ['shown', 'do_login_check'] : ['shown']);
    });
}
