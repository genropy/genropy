const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');

const GROUPLET_PY = path.join(__dirname, '../../resources/common/gnrcomponents/grouplet/grouplet.py');

function createContext({components = false} = {}) {
    const context = {console, File: function() {}, gnr: {}, genro: {}, setTimeout, navigator: {}, window: {}, document: {}};
    context.dojo = {
        Deferred: function() {},
        eval,
        hitch: (object, method) => (typeof method === 'string' ? object[method] : method).bind(object),
        forEach: (items, callback) => Array.prototype.forEach.call(items || [], callback),
        some: (items, callback) => Array.prototype.some.call(items || [], callback),
        toJson: JSON.stringify,
        isIE: 0,
        require() {},
        provide() {},
        declare(name, bases, members) {
            const base = Array.isArray(bases) ? bases[0] : bases;
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
    const sourceDir = process.env.GNR_JS_SOURCE || path.join(__dirname, '../gnr_d11/js');
    const sources = ['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js', 'genro_frm.js'];
    if (components) sources.push('genro_widgets.js', 'genro_components.js');
    for (const filename of sources) {
        vm.runInContext(readFileSync(path.join(sourceDir, filename), 'utf8'), context, {filename});
    }
    const groupletJs = path.join(__dirname, '../../resources/common/gnrcomponents/grouplet/grouplet.js');
    vm.runInContext(readFileSync(groupletJs, 'utf8'), context, {filename: 'grouplet.js'});
    context._T = str => str;
    context.genro.evaluate = expr => vm.runInContext('(' + expr + ')', context);
    context.genro.published = [];
    context.genro.publish = (topic, kw) => context.genro.published.push({topic, kw});
    return context;
}

function createForm(context, attrs = {}) {
    const watches = [];
    const sourceNode = {
        watch: (name, condition, callback) => watches.push({condition, callback})
    };
    const saved = [];
    const published = [];
    const form = Object.create(context.gnr.GnrFrmHandler.prototype);
    Object.assign(form, {
        sourceNode,
        table_name: 'Invoice',
        gridEditors: {},
        opStatus: null,
        changed: true,
        isValid: () => false,
        isNewRecord: () => false,
        getControllerData: () => null,
        fireControllerData: () => {},
        getCurrentPkey: () => 'PK1',
        publish: (topic, kw) => published.push({topic, kw}),
        do_save: kw => saved.push(kw)
    }, attrs);
    return {form, watches, saved, published};
}

function stubQuickDialog(context) {
    const dialogs = [];
    const node = () => ({_: (tag, name, attrs) => {
        if (typeof name === 'object') [name, attrs] = [undefined, name];
        dialogs.at(-1).children.push({tag, name, attrs});
        return node();
    }});
    context.genro.dlg = {
        quickDialog: () => {
            dialogs.push({children: []});
            return {center: node(), bottom: node(), show_action: () => {}, close_action: () => {}};
        }
    };
    return dialogs;
}

test('the Pending changes dialog offers Save unless the form opts out', () => {
    const context = createContext();
    const dialogs = stubQuickDialog(context);
    createForm(context).form.openPendingChangesDlg({});
    createForm(context, {pendingChangesSaveSlot: false}).form.openPendingChangesDlg({});
    const [regular, wizard] = dialogs.map(d => d.children);
    assert.equal(regular.find(c => c.tag === 'slotBar').attrs.slots, 'discard,*,cancel,save');
    assert.ok(regular.some(c => c.name === 'save'));
    assert.equal(wizard.find(c => c.tag === 'slotBar').attrs.slots, 'discard,*,cancel');
    assert.ok(!wizard.some(c => c.name === 'save'));
});

test('Shift on a dismiss does not save a form that opts out of Save', () => {
    const context = createContext();
    const dialogs = stubQuickDialog(context);
    const regular = createForm(context, {isValid: () => true});
    regular.form.load_store({destPkey: '*dismiss*', modifiers: 'Shift'});
    assert.equal(regular.saved.length, 1);
    assert.equal(dialogs.length, 0);
    const wizard = createForm(context, {isValid: () => true, pendingChangesSaveSlot: false});
    wizard.form.load_store({destPkey: '*dismiss*', modifiers: 'Shift'});
    assert.equal(wizard.saved.length, 0);
    assert.equal(dialogs.length, 1);
});

test('an explicit saveSlot argument still decides over the form option', () => {
    const context = createContext();
    const dialogs = stubQuickDialog(context);
    createForm(context, {pendingChangesSaveSlot: false}).form.openPendingChangesDlg({}, true);
    createForm(context).form.openPendingChangesDlg({}, false);
    assert.equal(dialogs[0].children.find(c => c.tag === 'slotBar').attrs.slots, 'discard,*,cancel,save');
    assert.equal(dialogs[1].children.find(c => c.tag === 'slotBar').attrs.slots, 'discard,*,cancel');
});

test('an autoSave form still saves on a dismiss whatever the option', () => {
    const context = createContext();
    const dialogs = stubQuickDialog(context);
    const auto = createForm(context, {isValid: () => true, autoSave: 500, pendingChangesSaveSlot: false});
    auto.form.load_store({destPkey: '*dismiss*'});
    assert.equal(auto.saved.length, 1);
    assert.equal(dialogs.length, 0);
});

function createStepNavigation(context, step) {
    const frameData = {step_index: 1, wizard_steps: new context.gnr.GnrBag()};
    frameData.wizard_steps.setItem('one', null);
    frameData.wizard_steps.setItem('two', null);
    context.genro.getFrameNode = () => ({
        getRelativeData: p => frameData[p.slice(1)],
        setRelativeData: (p, v) => { frameData[p.slice(1)] = v; }
    });
    context.genro.formById = () => step.form;
    return {frameData, grouplet: vm.runInContext('gnr_grouplet', context)};
}

test('Back saves a changed step at once, valid or not, and skips an unchanged one', () => {
    for (const isValid of [true, false]) {
        const context = createContext();
        const step = createForm(context, {allowSaveInvalid: true, isValid: () => isValid});
        const {frameData, grouplet} = createStepNavigation(context, step);
        grouplet.wizardGoTo(null, 0, 'wiz');
        assert.equal(frameData.step_index, 0);
        assert.equal(step.saved.length, 1);
        assert.ok(!step.published.some(p => p.topic === 'message'));
    }
    const context = createContext();
    const untouched = createForm(context, {allowSaveInvalid: true, changed: false});
    const {frameData, grouplet} = createStepNavigation(context, untouched);
    grouplet.wizardGoTo(null, 0, 'wiz');
    assert.equal(frameData.step_index, 0);
    assert.equal(untouched.saved.length, 0);
});

test('Back saves an incomplete step also when a grid editor is still open', () => {
    const context = createContext();
    const step = createForm(context, {allowSaveInvalid: true});
    const grid = {gnrediting: true};
    step.form.gridEditors = {rows: {grid}};
    const {frameData, grouplet} = createStepNavigation(context, step);
    grouplet.wizardGoTo(null, 0, 'wiz');
    assert.equal(frameData.step_index, 0);
    assert.equal(step.saved.length, 0);
    assert.equal(step.watches.length, 1);
    grid.gnrediting = false;
    assert.ok(step.watches[0].condition());
    step.watches[0].callback();
    assert.equal(step.saved.length, 1);
    assert.ok(!step.published.some(p => p.topic === 'message'));
});

function stepHook() {
    const match = readFileSync(GROUPLET_PY, 'utf8').match(/_onRemote="([^"]+)"/);
    assert.ok(match, 'groupletWizard passes an _onRemote hook to the step form');
    return match[1];
}

function buildStepForm(context, hook) {
    const built = [];
    const node = {
        _: (tag, attrs) => { built.push({tag, attrs}); return node; }
    };
    const sourceNode = {
        attr: {},
        gnrwdg: {},
        _registerNodeId() {},
        absDatapath: value => 'outer' + value.replace(/^\^/, ''),
        _: node._
    };
    const widget = new context.gnr.widgets.GroupletForm();
    widget.createContent(sourceNode, {
        formId: 'wiz_step_form', loadOnBuilt: true, value: '^.record', _onRemote: hook
    });
    return built.find(b => b.tag === 'grouplet').attrs._onRemote;
}

test('the step form built by GroupletForm registers itself in its parent form, then loads', () => {
    const context = createContext({components: true});
    context.gnr_grouplet = vm.runInContext('gnr_grouplet', context);
    const onRemote = buildStepForm(context, stepHook());
    const main = createForm(context, {table_name: 'Ticket', childForms: {}});
    const step = createForm(context, {formId: 'wiz_step_form', table_name: 'wiz_step_form',
                                      getParentForm: () => main.form});
    let loaded = 0;
    step.form.load = () => { loaded++; };
    context.funcCreate(onRemote, null, {form: step.form})();
    assert.equal(main.form.childForms.wiz_step_form, step.form);
    assert.equal(step.form.table_name, 'Ticket');
    assert.equal(loaded, 1);
});

test('the step hook runs alongside other remote hooks declaring the same names', () => {
    const context = createContext({components: true});
    context.gnr_grouplet = vm.runInContext('gnr_grouplet', context);
    const sibling = 'const frm = this.form; const parent = frm;';
    const onRemote = buildStepForm(context, sibling + ' ' + stepHook());
    const main = createForm(context, {childForms: {}});
    const step = createForm(context, {formId: 'wiz_step_form', getParentForm: () => main.form});
    step.form.load = () => {};
    context.funcCreate(onRemote, null, {form: step.form})();
    assert.equal(main.form.childForms.wiz_step_form, step.form);
});

test('registering a step without a parent form does nothing', () => {
    const context = createContext();
    const grouplet = vm.runInContext('gnr_grouplet', context);
    const step = createForm(context, {formId: 'wiz_step_form', table_name: 'wiz_step_form',
                                      getParentForm: () => null});
    grouplet.wizardRegisterStep(step.form);
    grouplet.wizardRegisterStep(null);
    assert.equal(step.form.table_name, 'wiz_step_form');
});

test('a rebuilt step replaces the previous one in the parent form', () => {
    const context = createContext();
    const grouplet = vm.runInContext('gnr_grouplet', context);
    const main = createForm(context, {childForms: {}});
    const first = createForm(context, {formId: 'wiz_step_form', getParentForm: () => main.form});
    const rebuilt = createForm(context, {formId: 'wiz_step_form', getParentForm: () => main.form});
    grouplet.wizardRegisterStep(first.form);
    grouplet.wizardRegisterStep(rebuilt.form);
    assert.deepEqual(Object.keys(main.form.childForms), ['wiz_step_form']);
    assert.equal(main.form.childForms.wiz_step_form, rebuilt.form);
});

function createWizard(context, {stepChanged = true} = {}) {
    const main = createForm(context, {changed: false, table_name: 'Ticket', childForms: {}});
    const loads = [];
    main.form.store = {getDefaultDestPkey: () => null};
    main.form.load_store = kw => loads.push(kw.destPkey);
    const step = createForm(context, {formId: 'wiz_step_form', changed: stepChanged,
                                      pendingChangesSaveSlot: false, getParentForm: () => main.form});
    step.form.store = {};
    step.form.doload_store = () => { step.form.changed = false; };
    step.form.publish = (topic, kw) => {
        if (topic === 'pendingChangesAnswer') step.form.pendingChangesAnswer(kw);
    };
    vm.runInContext('gnr_grouplet', context).wizardRegisterStep(step.form);
    return {step, main, loads};
}

function answer(dialog, command) {
    dialog.children.find(c => c.tag === 'slotBar').attrs.action.call({attr: {command}});
}

test('dismissing the wizard asks about the changed step, without Save: Cancel stays, Discard closes', () => {
    const context = createContext();
    const dialogs = stubQuickDialog(context);
    const {step, main, loads} = createWizard(context);
    main.form.load({destPkey: '*dismiss*'});
    assert.deepEqual(loads, []);
    assert.equal(dialogs[0].children.find(c => c.tag === 'slotBar').attrs.slots, 'discard,*,cancel');
    answer(dialogs[0], 'cancel');
    assert.deepEqual(loads, []);
    assert.equal(step.form.changed, true);
    main.form.load({destPkey: '*dismiss*'});
    answer(dialogs[1], 'discard');
    assert.equal(step.form.changed, false);
    assert.deepEqual(loads, ['*dismiss*']);
    assert.equal(dialogs.length, 2);
});

test('dismissing the wizard with an untouched step closes without asking', () => {
    const context = createContext();
    const dialogs = stubQuickDialog(context);
    const {main, loads} = createWizard(context, {stepChanged: false});
    main.form.load({destPkey: '*dismiss*'});
    assert.equal(dialogs.length, 0);
    assert.deepEqual(loads, ['*dismiss*']);
});

function createConfirm(context, attrs, {stepForm = null} = {}) {
    const data = {};
    const recordAttrs = {_draft: true};
    const main = createForm(context, Object.assign({
        isValid: () => true,
        getDataNodeAttributes: () => recordAttrs,
        updateDraftMarker: () => {},
        _buildInvalidMessage: () => 'invalid'
    }, attrs));
    Object.assign(main.form.sourceNode, {
        getRelativeData: p => data[p],
        setRelativeData: (p, v) => { data[p] = v; }
    });
    context.genro.getFrameNode = () => ({form: main.form});
    context.genro.formById = () => stepForm;
    const grouplet = vm.runInContext('gnr_grouplet', context);
    grouplet.wizardConfirm('wiz');
    return {data, recordAttrs, main};
}

test('Confirm leaves the record a draft when the save does not start', () => {
    const notStarted = createConfirm(createContext(), {do_save: () => undefined});
    assert.equal(notStarted.recordAttrs._draft, true);
    assert.equal(notStarted.data['.record.__is_draft'], true);
    assert.equal(notStarted.data['.wizard_confirming'], false);
    const refused = createConfirm(createContext(), {isValid: () => false});
    assert.equal(refused.recordAttrs._draft, true);
    assert.equal(refused.data['.wizard_confirming'], false);
});

test('Confirm marks nothing while the form is busy, and keeps the mark for a save under way', () => {
    const busy = createConfirm(createContext(), {opStatus: 'loading'});
    assert.equal(busy.recordAttrs._draft, true);
    assert.equal(busy.data['.wizard_confirming'], undefined);
    assert.equal(busy.main.saved.length, 0);
    let form;
    const saving = createConfirm(createContext(), {do_save: function() { form = this; this.opStatus = 'saving'; }});
    assert.equal(form, saving.main.form);
    assert.equal(saving.recordAttrs._draft, false);
    assert.equal(saving.data['.wizard_confirming'], true);
});

test('Confirm keeps the record confirmed when the save completes at once', () => {
    const done = createConfirm(createContext(), {do_save: function() {
        // onSaved, as the wizard's formsubscribe_onSaved controller does
        this.sourceNode.setRelativeData('.wizard_confirming', false);
    }});
    assert.equal(done.main.saved.length, 0);
    assert.equal(done.recordAttrs._draft, false);
    assert.equal(done.data['.record.__is_draft'], false);
    assert.equal(done.data['.wizard_confirming'], false);
});

test('Confirm with a deferred save leaves the record a draft, never wrongly confirmed', () => {
    const deferred = createConfirm(createContext(), {gridEditors: {rows: {grid: {gnrediting: true}}}});
    assert.equal(deferred.main.watches.length, 1);
    assert.equal(deferred.recordAttrs._draft, true);
    assert.equal(deferred.data['.wizard_confirming'], false);
});

test('Confirm saves a changed step first and confirms on its reload', () => {
    const context = createContext();
    let stepSave;
    const step = {isValid: () => true, changed: true, save: kw => { stepSave = kw; }};
    const pending = createConfirm(context, {do_save: function() { this.opStatus = 'saving'; }}, {stepForm: step});
    assert.equal(pending.recordAttrs._draft, true);
    assert.equal(typeof stepSave.onReload, 'function');
    stepSave.onReload();
    assert.equal(pending.recordAttrs._draft, false);
    assert.equal(pending.data['.wizard_confirming'], true);
    const blockedContext = createContext();
    const invalid = {isValid: () => false, changed: true, save: () => assert.fail('an invalid step is not saved')};
    const blocked = createConfirm(blockedContext, {}, {stepForm: invalid});
    assert.equal(blocked.recordAttrs._draft, true);
    assert.equal(blocked.main.saved.length, 0);
    assert.equal(blockedContext.genro.published[0].topic, 'floating_message');
});
