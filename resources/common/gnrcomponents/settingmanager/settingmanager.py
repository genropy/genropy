import json
import os

from gnr.core.gnrdecorator import public_method
from gnr.web.gnrbaseclasses import BaseComponent,page_proxy
from gnr.core.gnrbag import Bag
from gnr.core.gnrlang import gnrImport


@page_proxy
class SettingManager(BaseComponent):
    py_requires='gnrcomponents/framegrid:FrameGrid,gnrcomponents/formhandler:FormHandler'

    def setting_panel(self,parent,title=None,table=None,datapath=None,**kwargs):
        if self.isMobile:
            self.mobile_settings(parent,title=title,table=table,datapath=datapath,**kwargs)
        else:
            self.desktop_settings(parent,title=title,table=table,datapath=datapath,**kwargs)


    def mobile_settings(self,parent,title=None,table=None,datapath=None,**kwargs):
        pass

    
    def desktop_settings(self,parent,title=None,table=None,datapath=None,**kwargs):
        bc = parent.borderContainer(datapath=datapath,design='sidebar',_anchor=True,**kwargs)
        bc.data('.settings',self.get_setting_info(table=table))
        bc.dataFormula('.channel.store','blocksettings',blocksettings='=.settings',_onBuilt=True)
        frameCode = f'sm_{table.replace(".","_")}'
        self.channels_view(bc,title=title,region='left',width='300px',border_right='1px solid silver',splitter=True)

        sc = bc.stackContainer(region='center')
        view = self.channels_formlets_view(sc,frameCode=f'V_{frameCode}',pageName='formlets_view')
       
        form = view.grid.linkedForm(
            loadEvent='onRowClick',
            formRoot=sc,
            pageName='formlets_form',
            frameCode=f'F_{frameCode}',
            th_root=frameCode,
            datapath='#ANCHOR.formlets.form',
            childname='form')
        view.dataController("""frm.abort();
                                let formlets = settings.getItem(selectedId);
                                SET #ANCHOR.formlets.view.store = formlets?formlets.deepCopy():new gnr.GnrBag();
                                """,settings='=#ANCHOR.settings',
                        selectedId='^#ANCHOR.channel.grid.selectedId',frm=form.js_form,_delay=1)
        self.channels_formlets_form(form,table=table)

    def channels_view(self,parent,title=None,**kwargs):
        view = parent.contentPane(**kwargs).bagGrid(
            datapath='#ANCHOR.channel',
            storepath='#ANCHOR.channel.store',
            roundedEnvelope=True,
            title=title,
            grid_selected_caption='.selected_caption',
            struct=self.channel_struct
        )
        view.top.bar.replaceSlots('#','10,vtitle,*,searchOn,2',_class='mobileTemplateGridTop',toolbar=False)
        view.attributes['_class'] = "mobileTemplateGrid templateGrid"
        return view

    
        

    def channels_formlets_view(self,parent,frameCode=None,**kwargs):
        view = parent.contentPane(**kwargs).bagGrid(
            frameCode=frameCode,
            datapath='#ANCHOR.formlets.view',
            storepath='#ANCHOR.formlets.view.store',
            roundedEnvelope=True,
            struct=self.formlet_struct
        )
        bar = view.top.bar.replaceSlots('#','*,currtitle,*',_class='mobileTemplateGridTop',toolbar=False)
        bar.currtitle.div('^#ANCHOR.channel.grid.selected_caption?=#v|| "&nbsp;"')
        view.attributes['_class'] = "mobileTemplateGrid templateGrid"
        return view

        
    def channels_formlets_form(self,form,table=None,**kwargs):
        bar = form.top.slotBar('backTitle,*',height='30px',font_weight='bold',
                             color='var(--mainWindow-color)',border_bottom='1px solid silver')
        btn = bar.backTitle.lightButton(action="this.form.dismiss();",
                                       style='display:flex;align-items:center;',cursor='pointer')
        btn.div(_class="iconbox leftOut",height='25px',background_color='var(--mainWindow-color)')
        btn.div('^#ANCHOR.channel.grid.selected_caption?=#v|| "&nbsp;"')
        bc = form.center.borderContainer()
        bc.contentPane(region='center').remote(self.remoteDispatcher,setting_code='^#FORM.pkey',
                                                        channel_code='=#ANCHOR.channel.grid.selectedId',
                                                        table=table)




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
                            
    @public_method
    def remoteDispatcher(self,pane,setting_code=None,table=None,channel_code=None,**kwargs):
        if not setting_code:
            return
        data = self.db.table(table).getSettingData(setting_code=setting_code)
        print(xx)




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
                content.addItem(info['code'],None,formlet_path=setting_node.attr['rel_path'],**info)
        return result