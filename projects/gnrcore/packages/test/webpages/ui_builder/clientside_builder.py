# -*- coding: UTF-8 -*-
class GnrCustomWebPage(object):
    def main(self,root,**kwargs):
        root.attributes.update(overflow='hidden')
        frame = root.framePane(datapath='main')
        bar = frame.top.slotToolbar('10,run,*')
        bar.run.slotButton('Run',fire='.run')
        center = frame.center.borderContainer()
        left = center.contentPane(region='left',width='50%',splitter=True,border_right='1px solid silver')
        left.data('.jssource',"root._('div',{'innerHTML':'Hello world'})")
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
                                    //genro.dlg.alert("Error",e.toString());
                                }
                            """,_fired='^.run',jssource='=.jssource',right=right)
