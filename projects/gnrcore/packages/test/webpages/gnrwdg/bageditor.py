# -*- coding: utf-8 -*-

"""Editing a Bag through bagNodeEditor, bagEditor and multiValueEditor

The three widgets edit the same thing - the nodes of a Bag - at three levels of
detail: bagNodeEditor edits one node, bagEditor gives a tree plus a grid over a
whole Bag, and multiValueEditor edits a flat set of key/value pairs. The tree
cases load `adm/localization.xml` as a sample Bag with attributes worth showing
in columns.
"""

from gnr.core.gnrbag import Bag

LOCALIZATION_BAG = 'pkg:adm/localization.xml'

class GnrCustomWebPage(object):
    py_requires="gnrcomponents/testhandler:TestHandlerFull,gnrcomponents/framegrid:FrameGrid"
    
    def windowTitle(self):
        return 'bageditor'
         
    def localizationBag(self):
        """The adm localization.xml read as a Bag, sample data for the tree cases"""
        return Bag(self.site.storageNode(LOCALIZATION_BAG).internal_path)

    def test_0_firsttest(self,pane):
        """bagNodeEditor: edit the attributes of a single node, on the `test_editnode` topic"""
        bc = pane.borderContainer(height='400px',background='lime')
        bc.contentPane(region='top').button('load node',action='genro.publish("test_editnode","")')
        bc.contentPane(region='center').bagNodeEditor(bagpath='gnr',nodeId='test')
    
    def test_1_firsttest(self,pane):
        """A tree plus a bagGrid built by hand: the selected branch becomes rows, its attributes columns"""
        bc = pane.borderContainer(height='600px')
        b = self.localizationBag()
        bc.data('.treestore.root', b,label='Root')
        bc.contentPane(region='left',width='200px').tree(storepath='.treestore', labelAttribute='label',selectedPath='.selectedPath',hideValues=True)
        bc.dataController("""
            var rows = treestore.getItem(selectedpath);
            var struct = new gnr.GnrBag();
            var header = new gnr.GnrBag();
            struct.setItem('view_0.rows_0',header);
            var store = new gnr.GnrBag();
            var i = 0;
            header.setItem('cell_0',null,{field:'nodelabel',width:'12em',name:'Node Label'});
            if(rows && rows.len && rows.len()){
                rows.forEach(function(n){
                        var attr = objectUpdate({},n.attr);
                        for(var k in attr){
                            if(!header.getNodeByAttr('field',k)){
                                header.setItem('cell_'+genro.getCounter(),null,{field:k,width:'10em',name:k,dtype:guessDtype(attr[k]),edit:true});
                            }
                        }
                        attr.nodelabel = n.label;
                        store.setItem(n.label,new gnr.GnrBag(attr));
                        i++;
                    },'static');
            }
            SET .bageditor.grid.struct = struct;
            SET .bageditor.store = store;
            """,selectedpath='^.selectedPath',treestore='=.treestore')
        
        frame = bc.contentPane(region='center').bagGrid(storepath='.store',datapath='.bageditor',structpath='.struct',
                                            grid_selfDragRows=True,grid_selfsubscribe_addrow="""
                                                var that = this;
                                                genro.dlg.prompt('Add row',{lbl:'Nodelabel',action:function(result){
                                                        var b = that.widget.storebag();
                                                        b.setItem(result,new gnr.GnrBag({nodelabel:result}));
                                                    }});
                                            """,grid_selfsubscribe_addcol="""
                                                var that = this;
                                                genro.dlg.prompt('Add col',{'widget':[{lbl:'name',value:'^.field'},
                                                                                 {lbl:'dtype',value:'^.dtype',wdg:'filteringSelect',values:'T:Text,N:Number,B:Boolean'}],
                                                                            action:function(result){
                                                                                        var b = genro.getData(that.attrDatapath('structpath'));
                                                                                        var kw = result.asDict();
                                                                                        kw.name = kw.field;
                                                                                        kw.edit = true;
                                                                                        b.setItem('#0.#0.cell_'+genro.getCounter(),null,kw);
                                                                                    }
                                                                            });

                                            """)
        frame.top.bar.replaceSlots('addrow','addrow,addcol').addcol.slotButton('Add col',publish='addcol')

        bc.dataController("""
            var b = treestore.getItem(selectedPath);
            var nv = _node.getValue();
            if(_reason=='child'){
                if(_triggerpars.kw.updvalue){
                    var nl = _node.getParentNode().label;
                    var kw = {};
                    kw[_node.label] = _triggerpars.kw.value;
                    b.getNode(nl).updAttributes(kw);
                }else if(_triggerpars.kw.evt=='ins' && nv instanceof gnr.GnrBag){
                    var pos = branch.index(_node.label);
                    b.setItem(_node.label,null,_node.getValue().asDict(),{_position:pos>=0?pos:null});
                }else if(_triggerpars.kw.evt=='del' && nv instanceof gnr.GnrBag){
                    b.popNode(_node.label);
                }
            }
        """,branch='^.bageditor.store',selectedPath='=.selectedPath',treestore='=.treestore')

    def test_2_component(self,pane):
        """bagEditor: the same tree plus grid as test_1, as one widget with addrow/delrow/addcol"""
        b = self.localizationBag()
        pane.data('.treestore.root', b,label='Root')
        pane.borderContainer(height='600px').contentPane(region='center').bagEditor(storepath='.treestore.root',labelAttribute='label',addrow=True,delrow=True,addcol=True)



    def test_3_multiValueEditor(self,pane):
        """multiValueEditor on an empty datastore node: rows are added from the widget itself"""
        bc = pane.borderContainer(height='300px')

        bc.contentPane(region='center').multiValueEditor(value='^.dati')

    def test_4_multiValueEditor(self,pane):
        """multiValueEditor over a given dict, with tools=False so the pairs cannot be changed"""
        bc = pane.borderContainer(height='300px')
        bc.contentPane(region='center').multiValueEditor(value=dict(nome='Gianni',eta=33,indirizzo='via del pero 12'), 
                                                            tools=False)

    def test_5_prova(self, pane):
        """The same read-only multiValueEditor inside a moveable div, filling it at height 100%"""
        bc = pane.borderContainer(height='300px')
        center = bc.contentPane(region='center')
        m = center.div(lbl='Bellone', height='80px', width='300px', moveable=True, border='1px solid gray;')
        m.multiValueEditor(height='100%', value=dict(nome='Gianni',eta=33,indirizzo='via del pero 12'), 
                                                            tools=False)

