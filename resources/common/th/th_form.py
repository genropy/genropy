# -*- coding: UTF-8 -*-

# th_form.py
# Created by Francesco Porcari on 2011-05-04.
# Copyright (c) 2011 Softwell. All rights reserved.


from gnr.web.gnrwebstruct import struct_method
from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import extract_kwargs
from gnr.core.gnrbag import Bag
from gnr.core.gnrstring import boolean
from gnr.core.gnrdict import dictExtract


class TableHandlerForm(BaseComponent):
    py_requires="gnrcomponents/formhandler:FormHandler,gnrcomponents/batch_handler/batch_handler:TableScriptHandlerCaller"

    @struct_method
    def th_tableEditor(self,pane,frameCode=None,table=None,th_pkey=None,formResource=None,
                        formInIframe=False,readOnly=False,**kwargs):
        table = table or pane.attributes.get('table')
        self._th_mixinResource(frameCode,table=table,resourceName=formResource,defaultClass='Form') 
        options = self._th_hook('options',mangler=frameCode,dflt=dict())()
        options['readOnly'] = options.get('readOnly',readOnly)
       #slots = '*,|,semaphore,|,formcommands,|,dismiss,5,locker,5'
       #options['slots'] = options.get('slots',slots)
        options.update(kwargs)
        linkTo = pane        
        if hasattr(pane,'view'):
            grid =  pane.view.grid
            linkTo = grid
        #context_dbstore = pane.getInheritedAttributes().get('context_dbstore')
        form = linkTo.linkedForm(frameCode=frameCode,
                                 th_root=frameCode,
                                 datapath='.form',
                                 childname='form',
                                 table=table,
                                 formResource=formResource,
                                 iframe=formInIframe,
                                 #context_dbstore=context_dbstore,
                                 **options) 

        if formInIframe:
            return form
        self._th_applyOnForm(form,options=options,mangler=frameCode)   
        if table == self.maintable and hasattr(self,'th_form'):
            self.th_form(form)
        else:
            self._th_hook('form',mangler=frameCode)(form)
            
        pluggedFieldHandler = self._th_hook('pluggedFields',mangler=frameCode,defaultCb=self.th_defaultPluggedFieldHandler) 
        pluggedFieldHandler(form)
        return form
    
    def th_defaultPluggedFieldHandler(self,form):
        fb = form.getMainFormBuilder()
        if fb:
            fb.pluggedFields()

    @extract_kwargs(default=True,store=True,dialog=True,palette=True)
    @struct_method
    def th_thFormHandler(self,pane,formId=None,table=None,formResource=None,startKey=None,formCb=None,datapath=None,
                        store_kwargs=None,default_kwargs=None,dialog_kwargs=None,palette_kwargs=None,dbstore=None,**kwargs):
        tableCode = table.replace('.','_')
        formId = formId or tableCode
        self._th_mixinResource(formId,table=table,resourceName=formResource,defaultClass='Form')
        resource_options = self._th_hook('options',mangler=formId,dflt=dict())()
        resource_options.update(kwargs)
        formroot = pane._makeFormRoot(formId,dialog_kwargs=dialog_kwargs,palette_kwargs=palette_kwargs,form_kwargs=kwargs,datapath=datapath)
        if formroot is None:
            formroot = formroot or pane
        form = formroot.frameForm(frameCode=formId,formId=formId,table=table,
                             store_startKey=startKey,context_dbstore=dbstore,
                             datapath='.form',store='recordCluster',store_kwargs=store_kwargs,
                             **kwargs)
        self._th_applyOnForm(form,options=resource_options,mangler=formId)
        formCb = formCb or self._th_hook('form',mangler=formId)
        form.store.handler('load',default_kwargs=default_kwargs)
        formCb(form)
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
        form.dataController("""var title = newrecord?( newTitleTemplate? dataTemplate(newTitleTemplate,record): caption ): (titleTemplate? dataTemplate(titleTemplate,record) : tablename+': '+caption);
                            SET #FORM.controller.title = title;
                            this.form.publish('onChangedTitle',{title:title});
                            """,
                            tablename=self.db.table(table).name_long,
                            caption='^#FORM.record?caption',
                            newrecord='=#FORM.record?_newrecord',
                            record='=#FORM.record',titleTemplate=options.get('titleTemplate',False),
                            newTitleTemplate=options.get('newTitleTemplate',False))
        if form.attributes.get('form_isRootForm'):
            form.data('gnr.rootform.size',Bag(height=options.get('dialog_height','500px'),width=options.get('dialog_width','600px')))
        showtoolbar = boolean(options.pop('showtoolbar',True))
        navigation = options.pop('navigation',None)
        hierarchical = options.pop('hierarchical',None)   
        tree_kwargs = dictExtract(options,'tree_')     
        readOnly = options.get('readOnly')
        modal = options.get('modal',False)
        form.dataController(""" if(reason=='nochange' && modal){return;}
                                genro.dlg.alert(msg+' '+this.form.getRecordCaption()+': '+(reason=='invalid'?invalid:nochange),titledialog);""",
                            reason="^.controller.save_failed",_if='reason',
                            titledialog='!!Save failed',
                            msg='!!You cannot save',
                            invalid='!!Invalid record',
                            nochange='!!No change to save',modal=modal)
        box_kwargs = dictExtract(options,'box_')
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
            slots = '*'
            form.attributes.update(form_readOnly=True)
        if options.get('saveOnChange'):
            form.attributes.update(form_saveOnChange=True)
            showtoolbar = False
        if modal:
            slots='revertbtn,*,cancel,savebtn'
            form.attributes['hasBottomMessage'] = False
            bar = form.bottom.slotBar(slots,margin_bottom='2px',_class='slotbar_dialog_footer')
            bar.revertbtn.button('!!Revert',action='this.form.publish("reload")',disabled='^.controller.changed?=!#v')
            bar.cancel.button('!!Cancel',action='this.form.abort();')
            bar.savebtn.button('!!Save',iconClass='fh_semaphore',action='this.form.publish("save",{destPkey:"*dismiss*"})')  
          
        elif showtoolbar:
            default_slots = '*,form_delete,form_add,form_revert,form_save,semaphore,locker'
            if options.get('duplicate'):
                default_slots= default_slots.replace('form_add','form_add,form_duplicate')
            if hierarchical:
                default_slots = 'dismiss,hbreadcrumb,%s' %default_slots
            elif navigation:
                default_slots = 'navigation,%s' %default_slots
            elif options.get('selector'):
                default_slots = default_slots.replace('*','5,form_selectrecord,*')
            if options.get('printMenu'):
                #default_slots = default_slots.replace('form_delete','form_print,100,form_delete')
                extra_slots.append('form_print')

            if options.get('copypaste'):
                extra_slots.append('form_copypaste')
            if options.get('linker'):
                default_slots = default_slots.replace('form_delete','')
                default_slots = default_slots.replace('form_add','')
                #default_slots = default_slots.replace('locker','') 
            table = form.getInheritedAttributes()['table']  
            if extra_slots:
                default_slots = default_slots.replace('form_delete','%s,10,form_delete' %(','.join(extra_slots)))
            slots = options.get('slots',default_slots)
            if table == self.maintable:
                slots = 'logicalDeleter,%s' %slots 
            form.top.slotToolbar(slots)
        if not options.get('showfooter',True):
            form.attributes['hasBottomMessage'] = False
        if hierarchical:
            form.left.attributes.update(hidden=hierarchical=='closed',splitter=True)
            bar = form.left.slotBar('0,htreeSlot,0',width=tree_kwargs.pop('width','200px'),border_right='1px solid silver')
            bar.htreeSlot.treeViewer(**tree_kwargs)
            form.store.attributes.setdefault('startKey','*norecord*')
        for side in ('top','bottom','left','right'):
            hooks = self._th_hook(side,mangler=mangler,asDict=True)
            for hook in hooks.values():
                hook(getattr(form,side))    
        form.store.handler('load',onLoadingHandler=self._th_hook('onLoading',mangler=mangler))
        form.store.handler('save',onSavingHandler=self._th_hook('onSaving',mangler=mangler),
                                 onSavedHandler=self._th_hook('onSaved',mangler=mangler))
            
    
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
                    batch_table=table,batch_res_type='print',
                    batch_sourcepage_id=self.page_id)
        pane.dataRemote('.resources.print.menu',self.th_printMenu,table=table,cacheTime=5)
