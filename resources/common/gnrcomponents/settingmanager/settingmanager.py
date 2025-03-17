import json
import os

from gnr.core.gnrdecorator import public_method
from gnr.web.gnrbaseclasses import BaseComponent,page_proxy
from gnr.core.gnrbag import Bag
from gnr.core.gnrlang import gnrImport



class FormSetting(BaseComponent):
    def th_form(self,form):
        bar = form.top.slotBar('backTitle,*',height='30px',font_weight='bold',
                color='var(--mainWindow-color)',border_bottom='1px solid silver')
        bar.dataController("this.form.dismiss();",_fired='^#FORM.dismiss',_delay=1)
        btn = bar.backTitle.lightButton(action="""FIRE #FORM.dismiss;""",
                                       style='display:flex;align-items:center;',cursor='pointer')
        btn.div(_class="iconbox leftOut",height='25px',background_color='var(--mainWindow-color)')
        btn.div('^#ANCHOR.channel.grid.selected_caption?=#v|| "&nbsp;"')
        form.record.contentPane().remote(self.settingManagerRemoteDispatcher,
                                                        setting_code='^#FORM.record.setting_code',
                                                       channel_code='=#ANCHOR.channel.grid.selectedId',
                                                      table='=#FORM.controller.table')
      # form.record.remote(self.settingManagerRemoteDispatcher,setting_code='^#FORM.record.setting_code',
      #                                                 channel_code='=#ANCHOR.channel.grid.selectedId',
      #                                                 table=table)

    def th_options_showtoolbar(self):
        return False


    def th_options_autoSave(self):
        return True

    def th_options_firstAutoSave(self):
        return True


                            
    @public_method
    def settingManagerRemoteDispatcher(self,pane,setting_code=None,table=None,
                                            channel_code=None,
                                            mangling_code=None,**kwargs):
        if not setting_code:
            return

        path = f'formlet/{channel_code}/{setting_code}'
        self.mixinTableResource(table=table,path=path)
        self.flt_main(pane.contentPane(datapath='#FORM.record.setting_data'))




@page_proxy
class SettingManager(BaseComponent):
    py_requires='gnrcomponents/framegrid:FrameGrid,gnrcomponents/formhandler:FormHandler'

    def setting_panel(self,parent,title=None,table=None,datapath=None,frameCode=None,**kwargs):
        frameCode = frameCode or f'sm_{table.replace(".","_")}'

        frame = parent.framePane(frameCode=frameCode,datapath=datapath,design='sidebar',_anchor=True,rounded=8,**kwargs)
        frame.data('.settings',self.get_setting_info(table=table))
        frame.dataFormula('.channel.store','blocksettings',blocksettings='=.settings',_onBuilt=True)
        sc = frame.center.stackContainer(selectedPage='^#ANCHOR.selectedPage')
        self.channels_view(sc,title=title,pageName='channels_view')
        self.formlets_view(sc,frameCode=f'V_{frameCode}',pageName='formlets_view',table=table)
        self.formlets_form(sc,frameCode=f'V_{frameCode}',pageName='formlets_form',table=table)

        
        #form = bc.thFormHandler(table=table,formResource='gnrcomponents/settingmanager:FormSetting',
        #                    datapath='#ANCHOR.formlets.form')
        

    def channels_view(self,parent,title=None,**kwargs):
        view = parent.contentPane(**kwargs).bagGrid(
            datapath='#ANCHOR.channel',
            storepath='#ANCHOR.channel.store',
            roundedEnvelope=True,
            title=title,
            grid_selected_caption='.selected_caption',
            struct=self.channel_struct
        )
        bar = view.top.bar.replaceSlots('#','10,backTitle,*,searchOn,2',_class='mobileTemplateGridTop',toolbar=False)
        #btn = bar.backTitle.lightButton(action="genro.dom.windowMessage('parent',{'topic':'modal_page_close'});",
        #                               style='display:flex;align-items:center;',cursor='pointer')
        #btn.div(_class="iconbox leftOut",height='25px',background_color='var(--mainWindow-color)')
        #bar.backTitle.div(title)


        view.attributes['_class'] = "mobileTemplateGrid templateGrid"
        view.dataController("""let formlets = settings.getItem(selectedId);
                                SET #ANCHOR.formlets.view.store = formlets?formlets.deepCopy():new gnr.GnrBag();
                                SET #ANCHOR.selectedPage = 'formlets_view';
                                """,settings='=#ANCHOR.settings',
                        selectedId='^#ANCHOR.channel.grid.selectedId',#frm=form.js_form,
                        _delay=1)
        return view

    
        

    def formlets_view(self,parent,frameCode=None,table=None,**kwargs):
        view = parent.contentPane(**kwargs).bagGrid(
            frameCode=frameCode,
            datapath='#ANCHOR.formlets.view',
            storepath='#ANCHOR.formlets.view.store',
            roundedEnvelope=True,
            struct=self.formlet_struct
        )

        
        bar = view.top.bar.replaceSlots('#','10,backTitle,*,searchOn,2',_class='mobileTemplateGridTop',toolbar=False)

        btn = bar.backTitle.lightButton(action="SET #ANCHOR.selectedPage = 'channels_view' ;",
                                       style='display:flex;align-items:center;',cursor='pointer')
        btn.div(_class="iconbox leftOut",height='25px',background_color='var(--mainWindow-color)')
        btn.div('!![en]Back')

        view.attributes['_class'] = "mobileTemplateGrid templateGrid"
    
        return view


    def formlets_form(self,parent,frameCode=None,table=None,**kwargs):
        form = parent.contentPane(**kwargs).thFormHandler(table=table,formResource='gnrcomponents/settingmanager/settingmanager:FormSetting')
        parent.dataController("""
                                frm.goToRecord(pkey)""",
                            pkey='^#ANCHOR.formlets.view.grid.selectedId',frm=form.js_form,_delay=1)
        form.dataController("SET #ANCHOR.selectedPage = 'formlets_form' ;",formsubscribe_onLoaded=True)
        form.dataController("SET #ANCHOR.selectedPage = 'formlets_view' ;",formsubscribe_onDismissed=True)


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
        r.cell('formlet_path',hidden=True)
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




    def get_setting_info(self,table=None):
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
        for channelNode in resources:
            content = Bag()
            channel_attr = channelNode.attr
            channel_content = channelNode.value
            folder_path = channel_attr['abs_path']
            info_path = os.path.join(folder_path,f'{channelNode.label}.json')
            if os.path.exists(info_path):
                with open(info_path, 'r', encoding='utf-8') as f:
                    channel_info = json.loads(f.read())
            else:
                channel_info = {'caption':channel_attr.get('caption')}
            result.addItem(channelNode.label,content,**channel_info)
            for setting_node in channel_content:
                resmodule = gnrImport(setting_node.attr['abs_path'])
                info = getattr(resmodule, 'info',{})
                tags = info.get('tags')
                permissions = info.get('permissions')
                info['caption'] = info.get('caption') or setting_node.attr.get('caption')
                info['code'] = info.get('code') or setting_node.label
                if (tags and not self.application.checkResourcePermission(tags, self.userTags)) or \
                    permissions and not self.checkTablePermission(table=table,permissions=permissions):
                    continue
                if setting_node.label=='__pycache__':
                    continue
                content.addItem(info['code'],None,_pkey=tblobj.getSettingPkey(**info),**info)
        return result