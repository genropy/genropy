const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

class FakeElement {
    constructor() {
        this.style = {};
        this.attributes = {};
        this.listeners = {};
        this.parts = {};
        this.children = [];
        this.classes = new Set();
        this.classList = {add: c => this.classes.add(c), contains: c => this.classes.has(c)};
    }
    setAttribute(name, value) { this.attributes[name] = value; }
    appendChild(el) { el.parentNode = this; this.children.push(el); }
    removeChild(el) { this.children.splice(this.children.indexOf(el), 1); el.parentNode = null; }
    querySelector(selector) { return (this.parts[selector] ||= new FakeElement()); }
    addEventListener(name, fn) { (this.listeners[name] ||= []).push(fn); }
    fire(name) { (this.listeners[name] || []).forEach(fn => fn({stopPropagation() {}, target: this})); }
}

// The real GnrToast on a DOM stand-in; timers holds every auto-dismiss it schedules.
function createPage() {
    const timers = [];
    const body = new FakeElement();
    const context = {console, gnr: {}, genro: {},
                     setTimeout: (fn, ms) => timers.push(ms),
                     document: {body, createElement: () => new FakeElement()}};
    context.dojo = {
        subscribe() {},
        declare(name, base, members) {
            function Declared(...args) {
                if (Object.hasOwn(members, 'constructor')) members.constructor.apply(this, args);
            }
            Declared.prototype = Object.assign(Object.create(Object.prototype), members);
            const names = name.split('.');
            let namespace = context;
            for (const part of names.slice(0, -1)) namespace = namespace[part] ||= {};
            namespace[names.at(-1)] = Declared;
            return Declared;
        }
    };
    vm.createContext(context);
    const sourceDir = process.env.GNR_JS_SOURCE || path.join(__dirname, '../gnr_d11/js');
    for (const filename of ['gnrlang.js', 'genro_toast.js', 'genro_dev.js']) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    const genro = context.genro;
    genro.toast = new context.gnr.GnrToast();
    genro.dev = new context.gnr.GnrDevHandler();
    const shown = () => body.children.filter(el => el.className && el.className.startsWith('gnr-toast'));
    return {genro, timers, shown};
}

test('a refused save stays on screen until the user closes it', () => {
    const {genro, timers, shown} = createPage();
    genro.dev.handleRpcError('gnrexception', {getValue: () => 'The appointment is already confirmed'});
    const [toast] = shown();
    assert.equal(toast.className, 'gnr-toast gnr-toast-centered');
    assert.equal(toast.attributes['data-level'], 'error');
    assert.match(toast.innerHTML, /Warning.*The appointment is already confirmed/s);
    assert.deepEqual(timers, []);
    toast.fire('click');
    assert.equal(toast.classList.contains('gnr-toast-out'), false);
    toast.querySelector('.gnr-toast-close').fire('click');
    assert.equal(toast.classList.contains('gnr-toast-out'), true);
});
