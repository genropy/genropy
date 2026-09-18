const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const {test} = require('node:test');
const vm = require('node:vm');
const {loadPair} = require('../../../gnrjs/tests/bag_audit_harness.cjs');
const root = path.resolve(__dirname, '../../..');

// Execute the actual argument expressions from each caller against both real
// node implementations. Nullable fixtures preserve explicit null attributes.
const callers = [
 ['resources/common/gnrcomponents/framegrid.py', 'n.setAttr(updattr', 'var updattr={cell:null};', 'cell'],
 ['resources/common/gnrcomponents/htablehandler.py', 'editNode.setAttr(attr', 'var attr={caption:null};', 'caption', true],
 ['resources/common/gnrcomponents/doc_handler/doc_handler.py', 'pages.getNode(current).setAttr', 'var value=null;', 'caption'],
 ['resources/common/th/th_groupth.js', 'st_node.setAttr(st_row', 'var st_row={total:null};', 'total'],
 ['resources/common/th/th_groupth.js', 'n.setAttr(attr', 'var attr={total:null};', 'total'],
 ['resources/common/th/th_viewconfigurator.js', "setAttr(updDict,'_columnsetsEditor'", 'var updDict={width:null};', 'width'],
 ['resources/common/th/th_viewconfigurator.js', 'setAttr(updDict,reason', 'var updDict={width:null},reason="editor";', 'width'],
 ['projects/gnrcore/packages/adm/resources/frameindex.js', 'setAttr(this.iframeBagNodeAttr(kw)', 'var kw={}; this.iframeBagNodeAttr=function(){return {fullpath:null};};', 'fullpath'],
 ['projects/gnrcore/packages/adm/resources/frameindex.js', 'setAttr({fullname:kw.title}', 'var kw={title:null};', 'fullname'],
 ['projects/gnrcore/packages/adm/resources/frameplugin_menu/frameplugin_menu.py', 'setAttr(updater', 'var updater={badgeContent:null};', 'badgeContent'],
 ['projects/gnrcore/packages/adm/resources/frameplugin_menu/frameplugin_menu.py', 'setAttr({badgeContent:result}', 'var result=null;', 'badgeContent'],
 ['projects/gnrcore/packages/adm/resources/tables/group/th_group.py', 'setAttr(row', 'var row={tags:null};', 'tags'],
 ['projects/gnrcore/packages/adm/resources/tables/tblinfo_item/th_tblinfo_item.py', 'setAttr(row', 'var row={fullcaption:null};', 'fullcaption'],
 ['projects/gnrcore/packages/sys/resources/logging.js', 'setAttr(res.asDict()', 'var res=new gnr.GnrBag({level:null});', 'level'],
 ['projects/gnrcore/packages/test/webpages/gnrwdg/bageditor.py', 'setAttr(kw', 'var kw={field:null};', 'field'],
];

for (const [file, marker, setup, nullableKey, replacement] of callers) {
    test(`${file}: ${marker} retains the required attribute contract`, () => {
        const matches = readFileSync(path.join(root, file), 'utf8').split('\n').filter(line => line.includes(marker));
        assert.equal(matches.length, 1, 'Caller must remain uniquely identifiable');
        const line = matches[0];
        const invocation = line.slice(line.indexOf('.setAttr('));
        const pair = loadPair();
        for (const [name, context] of Object.entries(pair)) {
            const NodeClass = name === 'legacy' ? context.gnr.GnrBagNode : context.GenroBagJS.BagNode;
            context.callerNode = new NodeClass(null, 'row', null, {untouched: 'keep'});
            vm.runInContext(`${setup}\ncallerNode${invocation}`, context);
            const attrs = context.callerNode.attr;
            assert.equal(Object.hasOwn(attrs, nullableKey), true, name);
            assert.equal(attrs[nullableKey], null, name);
            assert.equal(Object.hasOwn(attrs, 'untouched'), !replacement, name);
        }
    });
}
