# -*- coding: utf-8 -*-
#--------------------------------------------------------------------------
# Copyright (c) : 2004 - 2007 Softwell sas - Milano 
# Written by    : Giovanni Porcari, Michele Bertoldi
#                 Saverio Porcari, Francesco Porcari , Francesco Cavazzana
#--------------------------------------------------------------------------
#This library is free software; you can redistribute it and/or
#modify it under the terms of the GNU Lesser General Public
#License as published by the Free Software Foundation; either
#version 2.1 of the License, or (at your option) any later version.

#This library is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
#Lesser General Public License for more details.

#You should have received a copy of the GNU Lesser General Public
#License along with this library; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA



"""
Component for menu handling:
"""

from gnr.web.gnrbaseclasses import BaseComponent

class MenuIframes(BaseComponent):
    css_requires='frameplugin_menu/frameplugin_menu'

    def mainLeft_iframemenu_plugin(self, tc):
        frame = tc.framePane(title="Menu", pageName='menu_plugin')
        frame.top.slotToolbar('2,searchOn,*',searchOn=True)
        if not self.isMobile:
            frame.bottom.slotToolbar('5,newWindow,*')
        bc = frame.center.borderContainer()
        self.mainLeft_clientLogo(bc.contentPane(region='bottom'))
        self.menu_iframemenuPane(bc.contentPane(region='center').div(position='absolute', top='2px', left='0', right='2px', bottom='2px', overflow='auto'))

    def mainLeft_clientLogo(self,pane):
        pane.contentPane(region='bottom').div(height='40px',margin='5px',_class='clientlogo')

    def btn_iframemenu_plugin(self,pane,**kwargs):
        pane.pluginButton('iframemenu_plugin',caption='!!Menu',
                            iconClass='iframemenu_plugin_icon',defaultWidth='210px')

                 
    def _menutree_getIconClass(self):
        if self.device_mode=='std':
            return """function(item,opened){
                        if(!item.attr.isDir){
                            return "treeNoIcon";
                        }
                        return opened? 'opendir':'closedir';                        
                    }"""
        return  "return 'treeNoIcon';"
    
    def _menutree_getLabelClass(self):
        if self.device_mode=='std':
            return """return node.attr.labelClass;"""
        return """let labelClass = node.attr.labelClass;
                if(node.attr.isDir){
                    let staticValue = node.getValue('static');
                    let resolver = node.getResolver();
                    if((!resolver || resolver.lastUpdate) && (!staticValue || staticValue.len()==0)){
                        return `label_emptydir ${labelClass}`;
                    }
                    let diricon = opened? 'label_opendir':'label_closedir';
                    return `${diricon} ${labelClass}`;
                }
                return labelClass;"""

    def _menutree_getLabel(self):
        return """
            let label = node.attr.label;
            if(node.attr.titleCounter && node.attr.isDir){
                let v = node.getValue();
                let count = v? v.len():0;
                if(count && node.attr.tag=="tableBranch" && node.attr.add_label){
                    count-=1;
                }
                label = `${label} (${count})`
            }
            return label;
        """

    def menu_iframemenuPane(self, pane, **kwargs):
        pane.data('gnr.appmenu',self.menu.getRoot())
        pane.dataController("genro.getDataNode('gnr.appmenu.root').refresh(true)",subscribe_refresh_appmenu=True)
        tree = pane.tree(id="_gnr_main_menu_tree", storepath='gnr.appmenu.root', selected_file='gnr.filepath',
                  labelAttribute='label',
                  hideValues=True,
                  _class='menutree',
                  persist='site',
                  inspect='AltShift',
                  identifier='#p',
                  device_mode=self.device_mode,
                  getIconClass=self._menutree_getIconClass(),
                    selectedLabelClass="menutreeSelected",
                  getLabel = self._menutree_getLabel(),
                  getLabelClass=self._menutree_getLabelClass(),
                  openOnClick=True,
                  connect_onClick="""
                  if($2.item.attr.isDir){
                        return;
                  }
                  this.publish('selectMenuItem',{fullpath:$1.getFullpath(null,true),
                                                                    relpath:$1.getFullpath(null,genro.getData(this.attr.storepath)),
                                                                  modifiers:$2.__eventmodifier});""",
                  autoCollapse=True,
                  selfsubscribe_selectMenuItem="""
                        var node = genro.getDataNode($1.fullpath);
                        var labelClass= node.attr.labelClass;
                        var inattr = node.getInheritedAttributes();    
                        var selectingPageKw = objectUpdate({name:node.label,pkg_menu:inattr.pkg_menu,"file":null,table:null,
                                                            formResource:null,viewResource:null,fullpath:$1.fullpath,
                                                            modifiers:$1.modifiers},node.attr);
                        if (genro.isMobile && false){
                            genro.framedIndexManager.makePageUrl(selectingPageKw);
                            genro.openWindow(selectingPageKw.url,selectingPageKw.label);
                        }
                        else if (selectingPageKw.externalWindow==true || selectingPageKw.modifiers == 'Shift'){
                            genro.publish("newBrowserWindowPage",selectingPageKw);
                        }else{
                            if(labelClass.indexOf('menu_existing_page')<0 && !node.attr.branchPage){
                                node.setAttribute('labelClass',labelClass+' menu_existing_page');
                            }   
                            this.publish("selected",selectingPageKw);
                        }    
                        if($1.doSelect){
                            this.widget.setSelectedPath(null,{value:node.getFullpath(null,genro.getData(this.attr.storepath))});
                        }
                        if(this.attr.device_mode!='std'){
                            genro.nodeById('standard_index').publish('hideLeft');
                        }
                  """,

                  nodeId='_menutree_')
        pane.dataController("""var flat_tblname = _node.label;
                                let store = treeNode.widget.storebag();
                                store.walk(function(n){
                                    if(n.attr.tag == "tableBranch" && n.attr.table.replace('.','_') == flat_tblname){
                                        n.refresh(true)
                                        let content = n.getValue();
                                        let child_count = (content instanceof gnr.GnrBag)?content.len():0;
                                        n.updAttributes({'child_count':child_count});
                                    }
                                },'static');
                               """,treeNode=tree,
                               dbChanges="^gnr.dbchanges")

   
       # pane.dataRpc('dummy',self.menu_refreshAppMenu,
       #             _onResult="""
       #                 genro.getDataNode('gnr.appmenu.root').refresh(true);
       #                 if(kwargs.selectPath){
       #                     kwargs._menutree.publish('selectMenuItem',{fullpath:kwargs.selectPath,doSelect:true}); 
       #                 }
       #             """,subscribe_refreshApplicationMenu=True,_menutree=menutree)


#################################### MOBILE MENU #########################################################################


    def mainLeft_mobilemenu_plugin(self, tc):
        frame = tc.framePane(title="Menu", pageName='mobilemenu_plugin')
        self.menu_iframemenuPane(frame.center.contentPane().div(position='absolute', top='2px', left='0', right='2px', bottom='2px', overflow='auto'))

    def btn_mobilemenu_plugin(self,pane,**kwargs):
        pane.pluginButton('mobilemenu_plugin',caption='!!Menu',
                            iconClass='iframemenu_plugin_icon',defaultWidth='210px')

