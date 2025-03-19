import json
import os

from gnr.core.gnrdecorator import public_method
from gnr.web.gnrbaseclasses import BaseComponent,page_proxy
from gnr.core.gnrbag import Bag
from gnr.core.gnrlang import gnrImport


class _FormBase(BaseComponent):
    @public_method
    def settingManagerRemoteDispatcher(self,pane,table=None,
                                            resource=None,resource_pkg=None,**kwargs):
        if not resource:
            return

        pkg,table = table.split('.')
        self.mixinComponent('tables/%s/%s' %(table,resource),safeMode=True)
        self.mixinComponent('tables/_packages/%s/%s/%s' %(pkg,table,resource),safeMode=True)

        self.flt_main(pane.contentPane(datapath='#FORM.record.setting_data'))


    @public_method
    def bagRemoteDispatcher(self,pane,table=None,resource=None,resource_pkg=None,**kwargs):
        if not resource:
            return

        pkg,table = table.split('.')
        self.mixinComponent('tables/%s/%s' %(table,resource),safeMode=True)
        self.mixinComponent('tables/_packages/%s/%s/%s' %(pkg,table,resource),safeMode=True)
        self.flt_main(pane)


class FormSetting(BaseComponent):
    py_requires='gnrcomponents/settingmanager/settingmanager:_FormBase'
    def th_form(self,form):
        form.record.contentPane().remote(self.settingManagerRemoteDispatcher,
                                                        fired='^#FORM.controller.loaded',
                                                       resource='=#ANCHOR.formlets.selected_resource',
                                                      table='=#FORM.controller.table')
      # form.record.remote(self.settingManagerRemoteDispatcher,setting_code='^#FORM.record.setting_code',
      #                                                 group='=#ANCHOR.channel.grid.selectedId',
      #                                                 table=table)

    def th_options_showtoolbar(self):
        return False


    def th_options_autoSave(self):
        return True

    def th_options_firstAutoSave(self):
        return True


                            





@page_proxy
class SettingManager(BaseComponent):
    css_requires='gnrcomponents/settingmanager/settingmanager'
    py_requires='gnrcomponents/framegrid:FrameGrid,gnrcomponents/formhandler:FormHandler,gnrcomponents/settingmanager/settingmanager:_FormBase'

    def setting_panel(self,parent,title=None,table=None,datapath=None,frameCode=None,storepath=None,**kwargs):
        frameCode = frameCode or f'sm_{table.replace(".","_")}'
        frame = parent.framePane(frameCode=frameCode,datapath=datapath,design='sidebar',_anchor=True,rounded=8,**kwargs)
        frame.data('.settings',self.getSettingsData(table=table))
        bc = frame.center.borderContainer()
        #self.channels_view(sc,title=title,pageName='channels_view')
        leftkw = {"region":"left","width":"100%"}
        if not self.isMobile:
            leftkw['width'] = '220px'
            leftkw['splitter'] = True
            leftkw['border_right'] = '1px solid silver'            
        self.formlets_tree(bc,frameCode=f'V_{frameCode}',title=title,table=table,**leftkw)
        if storepath:
            form = self.formlets_form_storepath(bc,frameCode=f'F_{frameCode}',table=table,region='center',storepath=storepath)
        else:
            form = self.formlets_form(bc,frameCode=f'F_{frameCode}',table=table,region='center')
        if self.isMobile:
            form.dataController("""bc.setRegionVisible('left',false)""",formsubscribe_onLoaded=True,bc=bc.js_widget)
            form.dataController("""bc.widget.setRegionVisible('left',true)
                                    """,formsubscribe_onDismissed=True,bc=bc)
        form.dataFormula("#FORM.current_caption","caption || '' ",caption='^#ANCHOR.formlets.selected_caption')
        if self.isMobile:
            bar = form.top.slotBar('backButton,5,formletTitle,*',height='30px',font_weight='bold',
                    color='var(--mainWindow-color)',border_bottom='1px solid silver')
            btn = bar.backButton.lightButton(action="""this.form.dismiss();""",
                                       style='display:flex;align-items:center;',cursor='pointer')
            btn.div(_class="iconbox menu_gray_svg",height='25px')
        else:
            bar = form.top.slotBar('*,formletTitle,*',height='30px',font_weight='bold',
                    color='var(--mainWindow-color)',border_bottom='1px solid silver')
        bar.formletTitle.div('^#FORM.current_caption')
    
    def formlets_tree(self,parent,title=None,**kwargs):
        frame = parent.framePane(**kwargs)
        frame.top.slotBar('5,searchOn,*,5',height='30px',font_weight='bold',
                color='var(--mainWindow-color)',border_bottom='1px solid silver')
        frame.center.contentPane().div(padding='10px').tree(
            storepath='#ANCHOR.settings',hideValues=True,
            _class='branchtree noIcon settings_tree',
            font_size='1.2em',labelAttribute='caption',
            openOnClick=True,
            getLabelClass="""
            if(!node.attr.formlet_caption){
                return 'setting_group';
            }
            """,
            connect_onClick="""
                  if($2.item.attr.resource){
                      FIRE #ANCHOR.formlets.load;
                  }
            """,
            selectedLabelClass='selectedTreeNode',
            selected_pkey='#ANCHOR.formlets.selected_pkey',
            selected_formlet_caption='#ANCHOR.formlets.selected_caption',
            selected_resource='#ANCHOR.formlets.selected_resource',
            selected_editing_path='#ANCHOR.formlets.editing_path'
        )


    def formlets_form(self,parent,frameCode=None,table=None,**kwargs):
        form = parent.contentPane(**kwargs).thFormHandler(table=table,formResource='gnrcomponents/settingmanager/settingmanager:FormSetting')
        parent.dataController("""
                                frm.goToRecord(pkey)""",
                            pkey='=#ANCHOR.formlets.selected_pkey',frm=form.js_form,
                            resource='^#ANCHOR.formlets.load',

                            _if='pkey',_delay=1)
        return form
        #form.dataController("SET #ANCHOR.selectedPage = 'formlets_form' ;",formsubscribe_onLoaded=True)
        #form.dataController("SET #ANCHOR.selectedPage = 'formlets_view' ;",formsubscribe_onDismissed=True)

        

    def formlets_form_storepath(self,parent,frameCode=None,table=None,storepath=None,**kwargs):
        form = parent.contentPane(**kwargs).frameForm(frameCode=frameCode,datapath='#ANCHOR.formlets.form')
        form.formstore(handler='memory',autoSave=500)
        parent.dataController("""
                                editing_path = editing_path || '_tempdata_'
                                if(editing_path=='_tempdata_'){
                                    genro.setData(editing_path,new gnr.GnrBag());
                                }else{
                                    editing_path = storepath+'.'+editing_path
                                }
                                frm.store.setLocationPath(editing_path)
                                frm.load();
                                """,
                            editing_path='=#ANCHOR.formlets.editing_path',
                            resource='^#ANCHOR.formlets.load',
                            frm=form.js_form,
                            storepath=storepath,_delay=1)
        form.record.contentPane().remote(self.bagRemoteDispatcher,
                                                        fired='^#FORM.controller.loaded',
                                                       resource='=#ANCHOR.formlets.selected_resource',
                                                      table=table)
        return form

    @public_method
    def saveSetting(self,record=None,table=None,setting_code=None,**kwargs):
        self.db.table(table).setSettingData(setting_code=setting_code,data=record)
        self.db.commit()



    def channel_struct(self,struct):
        r=struct.view().rows()
        r.cell('_settings',rowTemplate="""<div style='display:flex;align-items:center;justify-content:space-between;padding-top:5px;padding-bottom:5px;'>
                                                <div style='width:100%;display: flex;justify-content: space-between;flex-direction:column'>
                                                    <div style='font-weight:600'>$title</div>
                                                    <div style='font-size:.9em'>$caption</div>
                                                </div>
                                            </div>""",width='100%')
        r.cell('_right_in_icon',name=' ',width='23px',
                cellClasses='right_in_cell',cellStyles='vertical-align:middle',
                            format_onclick="this.publish('editrow',{pkey:this.widget.rowByIndex($1.rowIndex)._pkey,rowIndex:$1.rowIndex});",
                            format_isbutton=True
                            )
        



    def formlet_struct(self,struct):
        r=struct.view().rows()
        r.cell('group',hidden=True)
        r.cell('group_caption',name='Group',hidden=True)
        r.cell('_settings',rowTemplate="""<div style='display:flex;align-items:center;justify-content:space-between;padding-top:5px;padding-bottom:5px;'>
                                                <div style='font-weight:bold;width:12em'>$group_caption</div>
                                                <div style='width:100%;display: flex;justify-content: space-between;flex-direction:column'>
                                                    <div style='font-weight:600'>$title</div>
                                                    <div style='font-size:.9em'>$caption</div>
                                                </div>
                                            </div>""",width='100%')

        r.cell('_right_in_icon',name=' ',width='23px',
                cellClasses='right_in_cell',cellStyles='vertical-align:middle',
                            format_onclick="this.publish('editrow',{pkey:this.widget.rowByIndex($1.rowIndex)._pkey,rowIndex:$1.rowIndex});",
                            format_isbutton=True
                            )




    def getSettingsData(self,table=None):
        result = Bag()
        pkg,tblname = table.split('.')
        resources = Bag()
        resources_pkg = self.site.resource_loader.resourcesAtPath(page=self,pkg=pkg, 
                        path=f'tables/{tblname}/formlet')
        resources_custom = self.site.resource_loader.resourcesAtPath(page=self, 
                        path=f'tables/_packages/{pkg}/{tblname}/formlet')
        resources.update(resources_pkg)
        resources.update(resources_custom)
        tblobj = self.db.table(table)

        infodict = {groupNode.label:os.path.join(groupNode.attr['abs_path'],f'{groupNode.label}.json') for groupNode in resources_pkg}
        infodict.update({groupNode.label:os.path.join(groupNode.attr['abs_path'],
                            f'{groupNode.label}.json') for groupNode in resources_custom 
                            if groupNode.label not in infodict})
        for groupNode in resources:
            group_info = {'caption':groupNode.attr.get('caption')}
            content = Bag()
            group_info['group'] = groupNode.label
            result.addItem(groupNode.label,content,**group_info)
            for setting_node in groupNode.value:
                resmodule = gnrImport(setting_node.attr['abs_path'])
                info = getattr(resmodule, 'info',{})
                tags = info.get('tags')
                permissions = info.get('permissions')
                info['caption'] = info.get('caption') or setting_node.attr.get('caption')
                info['code'] = info.get('code') or setting_node.label
                info['priority'] = info.get('priority') or 0
                if (tags and not self.application.checkResourcePermission(tags, self.userTags)) or \
                    permissions and not self.checkTablePermission(table=table,permissions=permissions):
                    continue
                if setting_node.label=='__pycache__':
                    continue
                if setting_node.label=='__info__':
                    groupNode.attr.update(info)
                    continue
                info['formlet_caption'] = info['caption']
                content.setItem(info['code'],None,pkey=tblobj.getSettingPkey(**info),
                                resource= f'formlet/{groupNode.label}/{setting_node.label}',
                                group_caption=group_info.get('caption'),group=group_info.get('group'),
                                **info)
            content.sort('#a.priority,#a.caption')
        result.sort('#a.priority,#a.caption')
        return result