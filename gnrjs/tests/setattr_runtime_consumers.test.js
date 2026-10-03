const assert=require('node:assert/strict');
const {test}=require('node:test');
const {readFileSync}=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const {loadClasses}=require('./bag_audit_harness.cjs');
function runtime() {
    const c=loadClasses(['gnrlang.js','gnrbag.js','gnrdomsource.js','genro_bagjs_bundle.js','genro_wdg.js','genro_dom.js']);
    c.gnr.widgets={baseDojo:function(){}};
    vm.runInContext(readFileSync(path.join(__dirname,'../gnr_d11/js/genro_grid.js'),'utf8'),c);
    return c;
}
for(const mode of ['legacy','standalone']) {
    test(`grid edit preserves a null baseline with ${mode} attributes`,()=>{
        const c=runtime();const B=mode==='legacy'?c.gnr.GnrBag:c.GenroBagJS.Bag;
        const rowData=new B();const source=new B();source.setItem('row',null,{_pkey:'r1'});
        const row=source.getNode('row');row.attr.amount=null;
        if(!rowData.index) rowData.index=label=>rowData.keys().indexOf(label);
        let started;
        const rowEditor={data:rowData,startEditCell:column=>{started=column;}};
        const editor={grid:{rowIdByIndex:()=> 'r1',getRowEditor:()=>rowEditor}};
        c.gnr.GridEditor.prototype.startEditRemote.call(editor,row,'amount',0);
        assert.equal(started,'amount');
        assert.equal(Object.hasOwn(rowData.getNode('amount').attr,'_loadedValue'),true);
        assert.equal(rowData.getNode('amount').attr._loadedValue,null);
    });
    test(`grid update preserves null baseline with ${mode} attributes`,()=>{
        const c=runtime();const B=mode==='legacy'?c.gnr.GnrBag:c.GenroBagJS.Bag;
        const rowData=new B();if(!rowData.index) rowData.index=label=>rowData.keys().indexOf(label);
        const editor={grid:{rowFromBagNode:()=>({amount:null}),getRowEditor:()=>({data:rowData}),cellmap:{amount:{}}},updateStatus(){}};
        c.gnr.GridEditor.prototype.updateRow.call(editor,{}, {amount:5});
        assert.equal(rowData.getItem('amount'),5);
        assert.equal(Object.hasOwn(rowData.getNode('amount').attr,'_loadedValue'),true);
        assert.equal(rowData.getNode('amount').attr._loadedValue,null);
    });
    test(`attribute grid cell writes a named field and retains null with ${mode}`,()=>{
        const c=runtime();const B=mode==='legacy'?c.gnr.GnrBag:c.GenroBagJS.Bag;
        const b=new B();b.setItem('row',null,{kept:1});const node=b.getNode('row');
        const grid={cellmap:{amount:{}},datamode:'attr',dataNodeByIndex:()=>node};
        c.gnr.widgets.VirtualStaticGrid.prototype.patch_onApplyCellEdit.call(grid,null,0,'amount');
        assert.deepEqual({...node.attr},{kept:1,amount:null});
    });
}

test('checkbox callback updates the named attribute without replacing metadata',()=>{
    const c=runtime();const b=new c.GenroBagJS.Bag();b.setItem('row',null,{checked:true,kept:1});
    const node=b.getNode('row');const kw={value:'checked',name:'check',id:'check',label:'Check'};
    c.gnr.GnrDomHandler.prototype.html_checkbox.call({},kw,node);
    kw.onclick({target:{checked:false}});
    assert.deepEqual({...node.attr},{checked:false,kept:1});
});
test('grid whole-row attributes preserve nullable fields explicitly',()=>{
    const c=runtime();const b=new c.GenroBagJS.Bag();b.setItem('row',null,{name:'old'});
    const node=b.getNode('row');node.attr.empty=null;
    const data=new c.GenroBagJS.Bag({name:'new'});
    c.gnr.widgets.DojoGrid.prototype.mixin_rowBagNodeUpdate.call({rowBagNode:()=>node},0,data);
    assert.deepEqual({...node.attr},{name:'new',empty:null});
});
test('selectedValue is a partial update under the new attribute contract',()=>{
    const c=runtime();vm.runInContext(readFileSync(path.join(__dirname,'../gnr_d11/js/genro.js'),'utf8'),c);
    const b=new c.GenroBagJS.Bag();b.setItem('row',null,{kept:1});const node=b.getNode('row');
    c.genro.getDataNode=()=>node;
    c.gnr.GenroClient.prototype.setSelectedVal.call({}, {sourceNode:{}}, 'chosen');
    assert.deepEqual({...node.attr},{kept:1,selectedValue:'chosen'});
    c.gnr.GenroClient.prototype.setSelectedVal.call({}, {sourceNode:{}}, null);
    assert.deepEqual({...node.attr},{kept:1});
});
