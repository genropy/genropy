# -*- coding: UTF-8 -*-
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
from gnr.core.gnrbag import Bag,BagResolver

class MenuIframes(BaseComponent):
    css_requires='frameplugin_menu/frameplugin_menu'

    def mainLeft_iframemenu_plugin(self, tc):
        pane = tc.framePane(title="Menu", pageName='menu_plugin',)
        pane.bottom.slotToolbar('5,newWindow,*,searchOn',searchOn=True,searchOn_nodeId='_menutree__searchbox')
        self.menu_iframemenuPane(pane.div(position='absolute', top='2px', left='0', right='2px', bottom='2px', overflow='auto'))

    def btn_iframemenu_plugin(self,pane,**kwargs):
        pane.div(_class='button_block iframetab').div(_class='iframemenu_plugin_icon',tip='!!Menu',
                 connect_onclick="""PUBLISH open_plugin = "iframemenu_plugin";""",
                 nodeId='plugin_block_iframemenu_plugin')
                 
    def menu_iframemenuPane(self, pane, **kwargs):
        b = Bag()
        root_id = None
        customMenu = self.db.table('adm.menu').getMenuBag(root_id=root_id,userTags=self.userTags)
        if customMenu:
            b['root'] = customMenu 
        else:
            b['root'] = MenuResolver(path=getattr(self,'menu_path',None), pagepath=self.pagepath,_page=self)
            #b.getIndex()
        pane.data('gnr.appmenu', b)
        #leftPane = parentBC.contentPane(width='20%',_class='menupane',**kwargs)
        pane.tree(id="_gnr_main_menu_tree", storepath='gnr.appmenu.root', selected_file='gnr.filepath',
                  labelAttribute='label',
                  hideValues=True,
                  _class='menutree',
                  persist='site',
                  inspect='AltShift',
                  identifier='#p',
                  getIconClass="""function(item,opened){
                        if(!item.attr.isDir){
                            return "treeNoIcon";
                        }
                        return opened? 'opendir':'closedir';                        
                    }""",
                  getLabelClass="return node.attr.labelClass;",
                  openOnClick=True,
                  connect_onClick="""var labelClass= $1.attr.labelClass;
                                                 
                                    var inattr = $1.getInheritedAttributes();    
                                    var selectingPageKw = objectUpdate({name:$1.label,pkg_menu:inattr.pkg_menu,"file":null,table:null,
                                                                        formResource:null,viewResource:null,fullpath:$1.getFullpath(null,true),
                                                                        modifiers:$2.__eventmodifier},$1.attr);

                                    if (selectingPageKw.externalWindow==true || selectingPageKw.modifiers == 'Shift'){
                                        genro.publish("newBrowserWindowPage",selectingPageKw);
                                    }else{
                                        if(labelClass.indexOf('menu_existing_page')<0){
                                            $1.setAttribute('labelClass',labelClass+' menu_existing_page');
                                        }   
                                        this.publish("selected",selectingPageKw);
                                    }      
                                    
                                        """,
                  autoCollapse=True,
                  nodeId='_menutree_')


class MenuResolver(BagResolver):
    classKwargs = {'cacheTime': 300,
                   'readOnly': False,
                   'path': None,
                   'pagepath': None,
                   '_page':None}
    classArgs = ['path']


    def resolverSerialize(self):
        attr = super(MenuResolver, self).resolverSerialize()
        attr['kwargs'].pop('_page',None)
        return attr

    def load(self):
        sitemenu = self._page.application.siteMenu
        userTags = self._page.userTags
        result = Bag()
        level = 0
        if self.path:
            level = len(self.path.split('.'))
        for node in sitemenu[self.path]:
            allowed = True
            nodetags = node.getAttr('tags')
            filepath = node.getAttr('file')
            if nodetags:
                allowed = self._page.application.checkResourcePermission(nodetags, userTags)
            if allowed and filepath:
                allowed = self._page.checkPermission(filepath)
            if allowed:
                value=node.getValue()
                if node.resolver:
                    basepath='%(pkg)s/%(dir)s' % node.attr if 'dir' in node.attr else node.attr.get('basepath')
                    def cb(n):
                        n.attr['label']=n.attr.get('caption')
                        if n.attr.get('file_ext')== 'py':
                            n.attr['file']= '%s/%s' %(basepath,n.attr.get('rel_path'))
                        else:
                            n.attr['basepath']=basepath
                            n.attr['child_count']=len(n.value)
                    value.walk(cb)
                attributes = {}
                attributes.update(node.getAttr())
                labelClass = 'menu_level_%i' % level
           
                if isinstance(value, Bag):
                    attributes['isDir'] = True
                    newpath = '%s.%s' % (self.path, node.label) if self.path else node.label
                    value = MenuResolver(path=newpath, pagepath=self.pagepath,_page=self._page)()
                   # labelClass = 'menu_level_%i' % level
                else:
                    value = None
                    labelClass = '%s menu_page' %labelClass
                    if 'file' in attributes and  attributes['file'].endswith(self.pagepath.replace('.py', '')):
                        labelClass = 'menu_page menu_current_page'
                    if 'workInProgress' in attributes:
                        labelClass+=' workInProgress'
                customLabelClass = attributes.get('customLabelClass', '')
                attributes['labelClass'] = 'menu_shape %s %s' % (labelClass, customLabelClass)
                result.setItem(node.label, value, attributes)
        return result
            