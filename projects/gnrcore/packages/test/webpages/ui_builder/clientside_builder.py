# -*- coding: UTF-8 -*-
class GnrCustomWebPage(object):
    def main(self,root,**kwargs):
        root.attributes.update(overflow='hidden')
        frame = root.framePane(datapath='main')
        bar = frame.top.slotToolbar('10,run_legacy,10,run_fluent,*')
        bar.run_legacy.slotButton('Run legacy _()',fire='.run_legacy')
        bar.run_fluent.slotButton('Run fluent',fire='.run_fluent')
        center = frame.center.borderContainer()
        left = center.contentPane(region='left',width='50%',splitter=True,border_right='1px solid silver')
        left.data('.jssource_legacy',
            "root._('div',{'innerHTML':'Hello legacy'});\n"
            "root._('contentPane',{'innerHTML':'Legacy contentPane'});")
        left.data('.jssource_fluent',
            "root.div({'innerHTML':'Hello fluent'});\n"
            "root.ContentPane({'innerHTML':'Fluent ContentPane (CamelCase)'});\n"
            "root.contentpane({'innerHTML':'Fluent contentpane (lowercase)'});")
        left.codemirror(value='^.jssource_legacy',config_mode='javascript',
            config_addon='search,lint',config_lineNumbers=True,height='50%')
        left.codemirror(value='^.jssource_fluent',config_mode='javascript',
            config_addon='search,lint',config_lineNumbers=True,height='50%')
        right = center.contentPane(region='center',datapath='.center')
        runner = """var jscb = funcCreate(jssource,'root',this);
                    var root = genro.src.newRoot();
                    var box = root._('div',{});
                    try{
                        jscb(box);
                        var node = root.popNode('#0');
                        right._value.setItem(node.label,node._value,node.attr);
                    }catch(e){
                        genro.dlg.alert('Error',e.toString());
                    }"""
        frame.dataController(runner,_fired='^.run_legacy',jssource='=.jssource_legacy',right=right)
        frame.dataController(runner,_fired='^.run_fluent',jssource='=.jssource_fluent',right=right)
