const assert = require('node:assert/strict');
const {test} = require('node:test');
const vm = require('node:vm');
const {loadClasses} = require('./bag_audit_harness.cjs');

function setup() {
    const previous = process.env.GNR_JS_BAG;
    process.env.GNR_JS_BAG = 'genro-bag-js';
    let context;
    try {
        context = loadClasses(['gnrlang.js', 'gnrbag.js', 'gnrdomsource.js', 'genro_components.js']);
    } finally {
        if (previous === undefined) delete process.env.GNR_JS_BAG;
        else process.env.GNR_JS_BAG = previous;
    }
    context.genro.evaluate = source => vm.runInContext('(' + source + ')', context);
    context.genro.dom = {getEventModifiers: () => 'shift'};
    return context;
}

for (const command of [undefined, null, 'delete', '=current.command']) {
    test(`SlotButton publishes after raw BagNode removes null attributes: ${command}`, () => {
        const context = setup();
        const {gnr, GenroBagJS, genro} = context;
        let output;
        const source = {
            getInheritedAttributes: () => ({slotbarCode: 'query'}),
            _(tag, attrs) {
                output = new GenroBagJS.BagNode(null, 'generated', null, attrs);
                return output;
            }
        };
        const kwargs = {publish:'run', command};
        new gnr.widgets.SlotButton().createContent(source, kwargs);
        const attributes = {...output.attr};
        if (command == null) assert.equal(Object.hasOwn(attributes, 'command'), false);
        // The source evaluator normally resolves datasource references before funcApply.
        if (command === '=current.command') attributes.command = 'resolved';
        const events = [];
        genro.publish = (topic,payload) => events.push({topic,payload});
        const event = {shiftKey:true};
        context.funcApply(attributes.action, {...attributes,event,_counter:2});
        assert.equal(events.length,1);
        assert.equal(events[0].topic,'run');
        assert.equal(events[0].payload.command,command === '=current.command' ? 'resolved' : command || null);
        assert.equal(events[0].payload.evt,event);
        assert.equal(events[0].payload.modifiers,'shift');
        assert.equal(events[0].payload._counter,2);
    });
}

for (const original of [null,'previous']) {
    test(`selection external change preserves null baseline with raw BagNode: ${original}`, () => {
        const context = setup();
        const {gnr, GenroBagJS, dojo} = context;
        dojo.indexOf = (array,value) => array.indexOf(value);
        const editedRow = new gnr.GnrBag();
        const field = new GenroBagJS.BagNode(editedRow,'field','local',{caption:'Field'});
        editedRow._nodes._list.push(field);
        editedRow._nodes._dict.field = field;
        const data = new gnr.GnrBag();
        data.setItem('row',editedRow,{_pkey:'r1',field:original});
        const remoteNode = new GenroBagJS.BagNode(null,'row',null,{_pkey:'r1'});
        // Remote SQL row data can explicitly contain null, independent of node defaults.
        remoteNode.attr.field = null;
        const store = Object.create(gnr.stores.Selection.prototype);
        Object.assign(store,{
            linkedGrids:()=>[], getData:()=>data, len:()=>100,
            storeNode:{getAttributeFromDatasource:()=>null}
        });
        store.checkExternalChange([],['r1'],{r1:remoteNode},{r1:true});
        assert.equal(field.staticValue,'local');
        assert.equal(field.attr.caption,'Field');
        assert.equal(Object.hasOwn(field.attr,'_loadedValue'),true);
        assert.equal(field.attr._loadedValue,null);
    });
}
