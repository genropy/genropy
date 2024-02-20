# -*- coding: utf-8 -*-

# th_form.py
# Created by Francesco Porcari on 2011-05-04.
# Copyright (c) 2011 Softwell. All rights reserved.

from gnr.web.gnrwebstruct import struct_method
from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import extract_kwargs,public_method
from gnr.core.gnrbag import Bag
from gnr.core.gnrstring import boolean
from gnr.core.gnrdict import dictExtract


class TableHandlerForm(BaseComponent):
    py_requires="gnrcomponents/formhandler:FormHandler,gnrcomponents/batch_handler/batch_handler:TableScriptRunner"

    @extract_kwargs(dfltoption=True)
    @struct_method
    def th_tableEditor(self,pane,frameCode=None,table=None,th_pkey=None,formResource=None,
                        formInIframe=False,dfltoption_kwargs=None,**kwargs):
        table = table or pane.attributes.get('table')
        self._th_mixinResource(frameCode,table=table,resourceName=formResource,defaultClass='Form') 
        options = dfltoption_kwargs
        options.update(self._th_getOptions(frameCode))
        options.update(kwargs)
        options['store_startKey'] = options.get('store_startKey') or options.get('startKey')
        linkTo = pane        
        if hasattr(pane,'view'):
            grid =  pane.view.grid
            linkTo = grid
        #context_dbstore = pane.getInheritedAttributes().get('context_dbstore')
        remoteForm = options.pop('remote',None) or (self.getPreference('experimental.remoteForm',pkg='sys'))
        if formInIframe:
            remoteForm = False
        remotePars = dict()
        form = linkTo.linkedForm(frameCode=frameCode,
                                 th_root=frameCode,
                                 datapath='.form',
                                 childname='form',
                                 table=table,
                                 formResource=formResource,
                                 iframe=formInIframe,
                                 remoteForm=remoteForm,
                                 remotePars=remotePars,
                                 #context_dbstore=context_dbstore,
                                 **options) 
        if formInIframe:
            return form
        elif remoteForm:
            return self.th_prepareRemoteForm(form,**remotePars)
        return self.th_finalizeForm(form,table=table,options=options,frameCode=frameCode)
    
    def th_prepareRemoteForm(self,pane,formId=None,**kwargs):
        kw = dict()
        kw['nodeId'] = 'remote_wrapper_%s' %formId
        pane.contentPane(**kw).remote(self._th_remoteFormDispatcher,remoteFormId=formId,
                                            sendInheritedAttributes=True,**kwargs)

    @public_method
    def _th_remoteFormDispatcher(self,formRoot,remoteFormId=None,
                                    frameCode=None,th_root=None,datapath=None,childname=None,table=None,
                                 formResource=None,iframe=None,remoteForm=None,remotePars=None,**kwargs):
        form = formRoot.frameForm(formId=remoteFormId,frameCode=frameCode,
                                 th_root=th_root,datapath=datapath,childname=childname,
                                 table=table,formResource=formResource,
                                 iframe=iframe,**kwargs)
        formRoot.form = form
        form.store.handler('load',default_kwargs=kwargs.get('default_kwargs'))
        self._th_mixinResource(frameCode,table=table,resourceName=formResource,defaultClass='Form') 
        return self.th_finalizeForm(form,table=table,options=kwargs,frameCode=frameCode)
    
    def th_finalizeForm(self,form,table=None,options=None,frameCode=None,formCb=None):
        self._th_applyOnForm(form,options=options,mangler=frameCode)  
        if formCb:
            formCb(form)
        elif table == self.maintable and hasattr(self,'th_form'):
            self.th_form(form)
        else:
            self._th_hook('form',mangler=frameCode)(form)
        pluggedFieldHandler = self._th_hook('pluggedFields',mangler=frameCode,
                                            defaultCb=self.th_defaultPluggedFieldHandler)
        pluggedFieldHandler(form)
        return form
    
    def th_defaultPluggedFieldHandler(self,form):
        table = form.attributes.get('table')
        pluggedCols = self._th_getPluggedCols(table)
        mainfb = form.getMainFormBuilder()
        for f,pluggedBy,pluggedKwargs in pluggedCols:
            fb = None
            kwargs = dict() if pluggedKwargs is True else pluggedKwargs
            if pluggedBy:
                handler = getattr(self.db.table(pluggedBy),'onPlugToForm',None)
                if handler:
                    kwargs = handler(f)
            if kwargs is False:
                continue
            fbname = kwargs.pop('fbname',None)
            if fbname:
                fb = form.getFormBuilder(fbname,table=table)
            else:
                fb = mainfb
            formtable = form.attributes.get('table')
            if fb is not None:
                fbdbtable =fb.getInheritedAttributes().get('table')
                if formtable and fbdbtable!=formtable:
                    continue
                fb.field(f,**kwargs)

    def _th_getPluggedCols(self,table):
        tblobj = self.db.table(table)
        collist = list(tblobj.columns.items())+list(tblobj.model['virtual_columns'].items())
        return [(col,colobj.attributes.get('_pluggedBy'),colobj.attributes['plugToForm']) for col,colobj in collist if colobj.attributes.get('plugToForm')]


    @extract_kwargs(default=True,store=True,dialog=True,palette=True,tree=dict(slice_prefix=False,pop=True))
    @struct_method
    def th_thFormHandler(self,pane,formId=None,table=None,formResource=None,startKey=None,formCb=None,datapath=None,
                        store_kwargs=None,default_kwargs=None,dialog_kwargs=None,palette_kwargs=None,dbstore=None,
                        store='recordCluster',handlerType=None,tree_kwargs=None,**kwargs):
        tableCode = table.replace('.','_')
        formId = formId or tableCode
        self._th_mixinResource(formId,table=table,resourceName=formResource,defaultClass='Form')
        resource_options = self._th_getOptions(formId)
        resource_options.update(kwargs)
        resource_options.update(tree_kwargs)
        if not handlerType:
            if dialog_kwargs:
                handlerType = 'dialog'
            elif palette_kwargs:
                handlerType = 'palette'
        if handlerType:
            formroot = pane._makeFormRoot(formId,dialog_kwargs=dialog_kwargs,palette_kwargs=palette_kwargs,form_kwargs=kwargs,datapath=datapath,handlerType=handlerType)
        else:
            formroot = pane
            if datapath:
                formroot.attributes.update(datapath=datapath)
        if not self.checkTablePermission(table,'readonly'):
            resource_options['readOnly'] = True
        form = formroot.frameForm(frameCode=formId,formId=formId,table=table,
                             store_startKey=startKey,context_dbstore=dbstore,
                             datapath='.form',store=store,store_kwargs=store_kwargs,
                             **kwargs)
        form.store.handler('load',default_kwargs=default_kwargs)
        self.th_finalizeForm(form,table=table,options=resource_options,frameCode=formId,formCb=formCb)
        return form
        
    def _th_applyOnForm(self,form,options=None,mangler=None):
        if not self.th_checkPermission(form):
            form.attributes['_notallowed'] = True
            parent = form.parent
            if hasattr(parent,'view'):
                th_attributes =  parent.attributes
                th_class = th_attributes.get('_class') or ''
                th_attributes['_class'] = '%s th_form_not_allowed' %th_class
        table = form.getInheritedAttributes()['table']
        form.dataController("""var title = newrecord?( newTitleTemplate? dataTemplate(newTitleTemplate,record): caption ): (titleTemplate? dataTemplate(titleTemplate,record) : (caption||''));
                            
                            SET #FORM.controller.title = title;
                            this.form.publish('onChangedTitle',{title:title});
                            """,
                            tablename=self.db.table(table).name_long,
                            caption='=#FORM.record?caption',
                            newrecord='=#FORM.record?_newrecord',
                            record='=#FORM.record',titleTemplate=options.pop('titleTemplate',False),
                            newTitleTemplate=options.pop('newTitleTemplate',False),
                            _fired='^#FORM.controller.loaded')
        if form.attributes.get('form_isRootForm'):
            form.data('gnr.rootform.size',Bag(height=options.pop('dialog_height','500px'),width=options.pop('dialog_width','600px')))
        if 'lazyBuild' in options:
            form.attributes['_lazyBuild'] = options.pop('lazyBuild')
        if 'excludeCols' in options:
            form.attributes['excludeCols'] = options.pop('excludeCols')
        if 'fkeyfield' in options:
            form.attributes['fkeyfield'] = options.pop('fkeyfield')
        
        showtoolbar = boolean(options.pop('showtoolbar',True))
        navigation = options.pop('navigation',None)
        table = form.getInheritedAttributes()['table']  
        tblobj = self.db.table(table)
        use_hierarchical_stack =  hasattr(tblobj,'hierarchicalHandler') and tblobj.attributes['hierarchical']!='pkey'

        form_handlerType = form.attributes.get('form_handlerType')
        hierarchical = options.pop('hierarchical',use_hierarchical_stack and form_handlerType in ('stack',None))   
        tree_kwargs = dictExtract(options,'tree_',pop=True) 

        readOnly = options.pop('readOnly',False)
        modal = options.pop('modal',None) or dict()
        modal_modes = ('ask','confirm','navigation')
        if boolean(modal) and modal not in modal_modes:
            modal = dict(mode='ask' if not readOnly else 'confirm')
        elif isinstance(modal,str):
            modal = dict(mode=modal)
        
        modal.update(dictExtract(options,'modal_'))
        autoSave = options.pop('autoSave',False)
        firstAutoSave = options.pop('firstAutoSave',None)
        attachmentDrawer = options.pop('attachmentDrawer',None)

        draftIfInvalid= options.pop('draftIfInvalid',False)
        allowSaveInvalid= options.pop('allowSaveInvalid',draftIfInvalid)
        avoidFloatingMessage= options.pop('avoidFloatingMessage',draftIfInvalid)
        formCaption_kwargs = dictExtract(options,'formCaption_',pop=True) 
        formCaption = options.pop('formCaption',formCaption_kwargs)

        form_add = options.pop('form_add',True)
        form_save = options.pop('form_save',True)
        form_delete = options.pop('form_delete',True)
        form_archive = options.pop('form_archive',False)
        selector = options.pop('selector',False)
        annotations = options.pop('annotations',False)
        single_record = options.get('single_record') or options.pop('linker',False)

        form.attributes.update(form_draftIfInvalid=draftIfInvalid,form_allowSaveInvalid=allowSaveInvalid,form_avoidFloatingMessage=avoidFloatingMessage)
        if autoSave:
            form.store.attributes.update(autoSave=autoSave,firstAutoSave=firstAutoSave)

        form.dataController(""" if(reason=='nochange'){return;}
                                genro.dlg.alert(msg+' '+this.form.getRecordCaption()+': '+(reason=='invalid'?invalid:nochange),titledialog);""",
                            reason="^.controller.save_failed",_if='reason',
                            titledialog='!!Save failed',
                            msg='!!You cannot save',
                            invalid='!!Invalid record',
                            nochange='!!No change to save',modal=modal)
        box_kwargs = dictExtract(options,'box_',pop=True)
        extra_slots = []
        if hierarchical:
            box_kwargs['sidebar'] = True
            box_kwargs['persist'] = True
        if box_kwargs:
            sidebar = box_kwargs.pop('sidebar')
            if sidebar:
                box_kwargs['design'] = 'sidebar'
            form.attributes.update(**box_kwargs)
        
        if form.store.attributes.get('storeType') == 'Collection':
            if navigation is not False:
                navigation = True
        if readOnly:
            form.attributes.update(form_readOnly=True)
        if options.get('saveOnChange'):
            form.attributes.update(form_saveOnChange=options.pop('saveOnChange'))
            showtoolbar = False
        if 'parentLock' in options:
            form.attributes.update(form_parentLock=options.pop('parentLock'))
        if modal:
            self._th_handleModalBar(form,**modal)
        elif showtoolbar:
            default_slots = 'left_placeholder,*,right_placeholder,semaphore,5' if readOnly else 'left_placeholder,*,right_placeholder,form_archive,form_delete,form_add,form_revert,form_save,semaphore,locker'
            if annotations and not readOnly:
                default_slots = default_slots.replace('right_placeholder','right_placeholder,annotationTool')
            if form_add is False:
                default_slots = default_slots.replace('form_add','')
            if form_delete is False:
                default_slots = default_slots.replace('form_delete','')
            if form_save is False:
                default_slots = default_slots.replace('form_save','')
            if form_archive is False:
                default_slots = default_slots.replace('form_archive','')
            if options.pop('duplicate',False):
                default_slots= default_slots.replace('form_add','form_add,form_duplicate')
            if hierarchical:
                default_slots = 'dismiss,hbreadcrumb,%s' %default_slots
                options['form_add__class'] = 'add_sibling'
                options['form_duplicate__class'] = 'add_sibling'
                form.dataController("""genro.dom.setClass(this.form.sourceNode,'isLeafItem',isLeafItem)""",
                            isLeafItem='^#FORM.record?_isLeafItem')
                form.dataController("""genro.dom.setClass(this.form.sourceNode,'isRootItem',isLeafItem)""",
                            isLeafItem='^#FORM.record?_isRootItem')
            elif navigation:
                default_slots = 'navigation,%s' %default_slots
            if selector:
                default_slots = default_slots.replace('left_placeholder','form_selectrecord,left_placeholder')
                if isinstance(selector,dict):
                    options['form_selectrecord_pars'] = selector
            if options.pop('printMenu',False):
                #default_slots = default_slots.replace('form_delete','form_print,100,form_delete')
                extra_slots.append('form_print')
            actionMenu = options.pop('actionMenu',False)
            if actionMenu:
                #default_slots = default_slots.replace('form_delete','form_print,100,form_delete')
                extra_slots.append('form_action')
                options['form_action'] = actionMenu
            if options.pop('audit',False):
                extra_slots.append('form_audit')
            if options.pop('copypaste',False):
                extra_slots.append('form_copypaste')
            if single_record:
                default_slots = default_slots.replace('form_delete','')
                default_slots = default_slots.replace('form_add','')
            if extra_slots:
                default_slots = default_slots.replace('right_placeholder','right_placeholder,%s' %(','.join(extra_slots)))
            slots = options.pop('slots',default_slots)
            options.setdefault('_class','th_form_toolbar')
            form.top.slotToolbar(slots,form_add_defaults=form_add if form_add and form_add is not True else None,**options)
        if attachmentDrawer:
            self.mixinComponent("""gnrcomponents/attachmanager/attachmanager:AttachManager""")
            attachmentDrawer = dict() if attachmentDrawer is True else attachmentDrawer
            form.bottom.attachmentBottomDrawer(**attachmentDrawer)
        if hierarchical:
            form_attributes = form.attributes
            fkeyfield = form_attributes.get('fkeyfield')
            leftkw = dict(splitter=True)
            tree_kwargs['store_nodeId'] = f"{form.attributes.get('formId')}_hstore"
            if (hierarchical is True or hierarchical=='open'):
                form.store.attributes.setdefault('startKey','*norecord*')
                form.attributes.update(form_deleted_destPkey='*norecord*')
                form.attributes.update(form_isHierarchical=True)

                if hierarchical=='open':
                    leftkw['closable'] = 'open'      
            if hierarchical=='closed':
                leftkw['closable'] = 'close'
            if fkeyfield and  'condition' not in tree_kwargs:
                tree_kwargs['condition'] = '${fkeyfield}=:curr_{fkeyfield}'.format(fkeyfield=fkeyfield)
                tree_kwargs['condition_curr_{fkeyfield}'.format(fkeyfield=fkeyfield)] = '^#FORM/parent/#FORM.pkey'
            bar = form.left.slotBar('htreeSearchbar,htreeSlot,0',width=tree_kwargs.pop('width','200px'),border_right='1px solid silver',**leftkw)
            searchCode = form.attributes['frameCode']
            treeslots = '2,left_placeholder,searchOn,*,treeSortingTool,right_placeholder,2'
            hviewPicker = tree_kwargs.get('picker')
            if hviewPicker:
                treeslots = '2,left_placeholder,searchOn,*,treePicker,right_placeholder,2'
            tree_searchbar = bar.htreeSearchbar.slotToolbar(treeslots,searchOn=True,searchOn_searchCode=searchCode)
            tree_kwargs['searchCode'] = searchCode
            treeviewclass = tree_kwargs.get('_class')
            tree_kwargs['_class'] = f'{treeviewclass} hview' if treeviewclass else 'hview'
            tree = bar.htreeSlot.treeViewer(**tree_kwargs)
            if hviewPicker:
                self.th_hviewTreePicker(tree,search_bar=tree_searchbar,table=table,**tree_kwargs)
            


        for side in ('top','bottom','left','right'):
            hooks = self._th_hook(side,mangler=mangler,asDict=True)
            for hook in list(hooks.values()):
                hook(getattr(form,side))   
        if formCaption:
            formCaption = dict() if formCaption is True else formCaption
            kw = dict(height='25px',_class='formCaption',innerHTML='^.controller.title')
            kw.update(formCaption)
            form.top.div(**kw)

        defaultPrompt = options.get('defaultPrompt')
        if defaultPrompt:
            form.attributes['form_defaultPrompt']  = defaultPrompt
        options_default_kwargs = dictExtract(options,'default_',slice_prefix=False)
        
        form.store.handler('load',onLoadingHandler=self._th_hook('onLoading',mangler=mangler),**options_default_kwargs)
        form.store.handler('save',onSavingHandler=self._th_hook('onSaving',mangler=mangler),
                                 onSavedHandler=self._th_hook('onSaved',mangler=mangler))
        form._current_options = options

    def _th_handleModalBar(self,form,mode=None,**kwargs):
        if mode=='navigation':
            if form.store.attributes.get('storeType') == 'Collection':
                slots = 'dismissTitle,*,prevUp,nextDown'
            else:
                slots = 'dismissTitle'
                kwargs['dismissTitle_back_title'] = '!![en]Back'
            form.top.slotBar(slots,height=kwargs.pop('height','30px'),font_weight=kwargs.pop('font_weight','bold'),
                             color=kwargs.pop('color','var(--mainWindow-color)'),border_bottom=kwargs.pop('border','1px solid silver'),
                            **kwargs)
        else:
            slots= '*,cancel' if mode=='confirm' else 'revertbtn,*,cancel,savebtn'
            bar = form.bottom.slotBar(slots,margin_bottom='2px',_class='slotbar_dialog_footer')
            bar.cancel.button('!!Cancel' if not mode=='confirm' else '!![en]Close',action='this.form.abort();')
            if mode=='ask':
                bar.revertbtn.button('!!Revert',action='this.form.publish("reload")',disabled='^.controller.changed?=!#v')
                bar.savebtn.button('!!Save',iconClass='fh_semaphore',action='this.form.publish("save",{destPkey:"*dismiss*"})')
            


    @struct_method
    def td_slotbar_annotationTool(self,pane,frameCode=None,annotationTool=None,**kwargs):
        if self.db.package('orgn') and self.getPreference('organizer_enabled',pkg='orgn'):
            self.mixinComponent('orgn_components:OrganizerComponent')
            pane.annotationTool(**kwargs)
        else:
            pane.div()

    @struct_method          
    def th_slotbar_form_audit(self,pane,**kwargs):
        inattr = pane.getInheritedAttributes()
        th_root = inattr['th_root']
        pane.paletteGrid(paletteCode='%s_recordHistory' %th_root,
                        title='!!Record History',
                        dockButton=True,
                        width='400px',
                        height='500px',
                        readOnly=True,
                        dockButton_iconClass='iconbox book',
                        viewResource='ViewRecordHistory',table='adm.audit',
                        condition='$tablename=:tname AND $record_pkey=:pk',
                        condition_tname='=#FORM.controller.table',
                        condition_pk='^#FORM.pkey',
                        view_store_onBuilt=True,
                        formResource='FormRecordHistory',
                        thwidget='border')

    @struct_method          
    def th_slotbar_form_copypaste(self,pane,**kwargs):
        pane.dataController("""var form = this.form;
                                var cb = function(){return form.copyPasteMenu()};
                                SET .controller.copypaste.menu = new gnr.GnrBagCbResolver({method:cb});""",
                        _onStart=True)
        pane.div(tip='!!Copy and paste',_class='iconbox case').menu(storepath='#FORM.controller.copypaste.menu',_class='smallmenu',modifiers='*')


    @struct_method          
    def th_slotbar_form_print(self,pane,**kwargs):
        inattr = pane.getInheritedAttributes()
        table = inattr['table']
        pane.div(_class='iconbox print').menu(modifiers='*',storepath='.resources.print.menu',_class='smallmenu',
                    action="""
                            var kw = objectExtract(this.getInheritedAttributes(),"batch_*",true);
                            kw.resource = $1.resource;
                            if($1.template_id){
                                kw.extra_parameters = new gnr.GnrBag({template_id:$1.template_id,table:kw.table});
                                kw.table = null;
                            } 
                            kw['pkey'] = this.form.getCurrentPkey();
                            genro.publish("table_script_run",kw)
                            """,
                    batch_table=table,batch_res_type='print')
        pane.dataRemote('.resources.print.menu',self.th_printMenu,table=table,cacheTime=5)


    @struct_method          
    def th_slotbar_form_action(self,pane,form_action=None,**kwargs):
        inattr = pane.getInheritedAttributes()
        table = inattr['table']
        pane.div(_class='iconbox gear').menu(modifiers='*',storepath='.resources.action.menu',_class='smallmenu',
                    action="""
                            var kw = objectExtract(this.getInheritedAttributes(),"batch_*",true);
                            kw.pkey = this.form.getCurrentPkey();
                            var sourceNode = this;
                            var menuattr = $1;
                            var onResult,onCalling;
                            if (menuattr.onResult) {
                                onResult = funcCreate(menuattr.onResult, 'result,kwargs,old', this);
                            }
                            if (menuattr.onCalling) {
                                onCalling = funcCreate(menuattr.onCalling, 'kwargs', this);
                            }
                            var finalize = function(_askResult){
                                if(_askResult){
                                    objectUpdate(kw,_askResult);
                                }
                                if(menuattr.rpcmethod){
                                    objectUpdate(kw,objectExtract($1,'rpc_*',true));
                                    kw._sourceNode = sourceNode;
                                    if(onCalling){
                                        onCalling(kw);
                                    }
                                    if(menuattr.lockScreen){
                                        genro.lockScreen(true,sourceNode.getStringId(),menuattr.lockScreen);
                                    }
                                    return genro.serverCall(menuattr.rpcmethod,kw,function(result){
                                        if(onResult){
                                            onResult(result,kw);
                                        }
                                        if(menuattr.lockScreen){
                                            genro.lockScreen(false,sourceNode.getStringId());
                                        }
                                    });
                                }
                                kw.resource = menuattr.resource;
                                if(menuattr.template_id){
                                    kw.extra_parameters = new gnr.GnrBag({template_id:menuattr.template_id,table:kw.table});
                                    kw.table = null;
                                } 
                                genro.publish("table_script_run",kw)
                            }
                            if($1.askParameters){
                                return genro.dlg.askParameters(finalize,$1.askParameters,kw,this)
                            }else{
                                finalize();
                            }
                            """,
                    batch_table=table,batch_res_type='action')
        pane.dataRemote('.resources.action.menu',self.table_script_resource_tree_data,table=table,res_type='action',topic=form_action,cacheTime=5)
