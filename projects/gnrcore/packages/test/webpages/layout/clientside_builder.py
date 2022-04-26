# -*- coding: utf-8 -*-

# Created by Francesco Porcari on 2011-02-26 and updated by Davide Paci on 2022-01-19.
# Copyright (c) 2011 Softwell. All rights reserved.

"Javascript page construction"

class GnrCustomWebPage(object):
    user_polling=0
    auto_polling=0

    def main(self,pane,**kwargs):
        "Page can be built through javascript dynamically as well"
        pane.attributes.update(overflow='hidden')
        frame = pane.framePane(datapath='main')
        bar = frame.top.slotToolbar('10,run,*')
        bar.run.slotButton('Run',fire='.run')
        center = frame.center.borderContainer()
        left = center.contentPane(region='left',width='50%',splitter=True,border_right='1px solid silver')
        left.data('.jssource',"bc = root._('borderContainer',{height:'300px',border:'solid 2px red'});\ntop = bc._('contentPane',{region:'top',height:'200px',background:'blue'});\ncenter = bc._('contentPane',{region:'center',background:'green'});")
        left.codemirror(value='^.jssource',config_mode='javascript',
                                            config_addon='search,lint',
                                            config_lineNumbers=True,height='100%')
        right = center.contentPane(region='center',datapath='.center')
        frame.dataController("""var jscb = funcCreate(jssource,'root',this);
                                var root = genro.src.newRoot();
                                var box = root._('div',{});
                                try{
                                    jscb(box);
                                    var node = root.popNode('#0')
                                    right._value.setItem(node.label,node._value,node.attr);
                                }catch(e){
                                    console.log('uuu')
                                    //genro.dlg.alert("Error",e.toString());
                                }
                            """,_fired='^.run',jssource='=.jssource',right=right)