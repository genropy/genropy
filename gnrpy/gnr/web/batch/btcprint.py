#!/usr/bin/env python
# encoding: utf-8
#
#btcprint.py
#
#Created by Francesco Porcari on 2010-10-16.
#Copyright (c) 2011 Softwell. All rights reserved.

from gnr.web.batch.btcbase import BaseResourceBatch
from gnr.core.gnrstring import slugify
from gnr.core.gnrbag import Bag
import os


class BaseResourcePrint(BaseResourceBatch):
    """Base resource to make a :ref:`print`"""
    batch_immediate = False
    #dialog_height = '300px'
    #dialog_width = '460px'
    #dialog_height_no_par = '245px'
    html_res = ''
    mail_address = ''
    mail_tags = 'admin'
    templates = '' #CONTROLLARE
    batch_schedulable = False
    batch_ask_options = 'sys.print.ask_options_enabled'
    batch_print_modes = ['pdf','server_print','mail_pdf','mail_deliver']
    batch_mail_modes = ['mail_pdf','mail_deliver']

    def __init__(self, *args, **kwargs):
        super(BaseResourcePrint, self).__init__(**kwargs)
        batch_print_modes = self.db.application.getPreference('.print.modes',pkg='sys')
        self.print_res  = getattr(self,'html_res', None) or getattr(self,'rlab_res', None)
        if batch_print_modes:
            self.batch_print_modes = batch_print_modes.split(',')
        if self.print_res:
            self.htmlMaker = self.page.site.loadTableScript(page=self.page, table=getattr(self,'maintable',None),
                                                            respath=self.print_res, class_name='Main')
        else:
            self.htmlMaker = None
        if not hasattr(self, 'mail_tags'):
            self.mail_tags = 'mail'


    def _pre_process(self):
        self.pre_process()
        self.batch_options = self.batch_parameters.get('batch_options') or {}
        self.print_mode = self.batch_options.get('print_mode','pdf')
        self.server_print_options = self.batch_parameters.get('_printerOptions') or {}
        self.print_options = self.batch_options.get(self.print_mode) or {}
        self.network_printer = self.page.getService('networkprint')
        self.pdf_handler = self.page.getService('pdf')
        self.pdf_make = self.print_mode != 'client_print'

    def print_selection(self, thermo_selection=None, thermo_record=None):
        thermo_s = dict(line_code='selection', message='get_record_caption', tblobj=self.tblobj)
        thermo_s.update(thermo_selection or {})
        thermo_r = dict(line_code='record', message='get_record_caption')
        thermo_r.update(thermo_record or {})
        if isinstance(thermo_s['message'], str) and hasattr(self, thermo_s['message']):
            thermo_s['message'] = getattr(self, thermo_s['message'])
        if isinstance(thermo_r['message'], str) and hasattr(self.htmlMaker, thermo_r['message']):
            thermo_r['message'] = getattr(self.htmlMaker, thermo_r['message'])
        records = self.get_records()
        pkeyfield = self.tblobj.pkey
        if not self.get_selection():
            return
        for k,record in self.btc.thermo_wrapper(records, maximum=len(self.get_selection()),enum=True ,**thermo_s):
            self.print_record(record=record, thermo=thermo_r, storagekey=record[pkeyfield],idx=k)


    def export_selection_data(self):
        for record in self.get_records():
            yield self.htmlMaker.getExportData(record=record,parent=self,**self.batch_parameters)
    
    def export_record_data(self,record=None):
        return [self.htmlMaker.getExportData(record=record,parent=self,**self.batch_parameters)]
                

    def print_record(self, record=None, thermo=None, storagekey=None,idx=None):
        self.onRecordPrinting(record)
        result = self.do_print_record(record=record)
        self.onRecordExit(record)
        if not result:
            return
        if self.onRecordPrinted(record=record,filepath=result) is not False:
            self.storeResult(storagekey, result, record, filepath=getattr(self.htmlMaker,'filepath',result))

    def do_print_record(self,record=None,idx=None,thermo=None):
        result = None
        if self.htmlMaker.cached:
            self.htmlMaker.record = record
            result = self.htmlMaker.getPdfPath()
            self.htmlMaker.filepath = result
            if not os.path.isfile(result):
                result = None
        if not result:
            result = self.htmlMaker(record=record,record_idx=idx, thermo=thermo, pdf=self.pdf_make,
                                **self.batch_parameters)
        return result
    

    def onRecordExit(self, record=None):
        """Hook method.
        
        :param record: the result records of the executed batch"""
        pass
    
    def onRecordPrinting(self,record):
        return 

    def onRecordPrinted(self,record=None,filepath=None):
        return

    def do(self):
        if 'templates' not in self.batch_parameters:
            self.batch_parameters['templates'] = self.templates  #CONTROLLARE
        if self.htmlMaker and self.htmlMaker.maintable == self.htmlMaker.row_table:
            self.htmlMaker.row_table = self.tblobj.fullname
            self.print_record(record=Bag(dict(selectionPkeys=self.get_selection_pkeys())))
        else:
            return self.print_selection()

    def get_export_data(self,export_mode=None,selectionName=None,selectedRowidx=None,**kwargs):
        #metto le cose in self, selection_name,export_mode
        #poi modalita singola o estesa
        self.export_mode = export_mode
        self.defineSelection(selectionName=selectionName,selectedRowidx=selectedRowidx)
        self.batch_parameters = dict(kwargs)
        if self.htmlMaker and self.htmlMaker.maintable == self.htmlMaker.row_table:
            self.htmlMaker.row_table = self.tblobj.fullname
            return self.export_record_data(record=Bag(dict(selectionPkeys=self.get_selection_pkeys())))
        else:
            return self.export_selection_data()
        
    def get_record_caption(self, item, progress, maximum, **kwargs):
        caption = '%s (%i/%i)' % (self.tblobj.recordCaption(item),
                                  progress, maximum)
        return caption
        
    def result_handler(self):
        resultAttr = dict()
        result = getattr(self, 'result_handler_%s' % self.print_mode)(resultAttr)
        result = result or ''
        return result, resultAttr

    @property
    def mail_preference(self):
        return self.page.site.getService('mail').getDefaultMailAccount()
        
    def result_handler_mail_deliver(self, resultAttr):
        mailmanager = self.page.getService('mail')
        mailpars = dict()
        mailpars.update(self.mail_preference.asDict(True))
        mailpars.update(self.print_options.asDict(True))

        for pkey, result in list(self.results.items()):
            record = self.records[pkey]
            mailpars['attachments'] = [result]
            mailpars['to_address'] = record[self.mail_address]
            mailmanager.sendmail(**mailpars)

    def result_handler_mail_pdf(self, resultAttr):
        mailmanager = self.page.getService('mail')
        mailpars = dict()
        mailpars.update(self.mail_preference.asDict(True))
        mailpars.update(self.print_options.asDict(True))
        mailpars['attachments'] = list(self.results.values())
        mailmanager.sendmail(**mailpars)
        
    def result_handler_server_print(self, resultAttr):
        printer = self.network_printer.getPrinterConnection(self.server_print_options.pop('printer_name'),
                                                          **self.server_print_options.asDict(True))
        return printer.printFiles(list(self.results.values()), self.batch_title)


    def result_handler_html(self, resultAttr):
        print(x)
        
    def result_handler_pdf(self, resultAttr):
        if not self.results:
            return '{btc_name} completed'.format(btc_name=self.batch_title), dict()
        save_as = slugify(self.print_options.get('save_as') or self.batch_parameters.get('save_as') or '')
        if not save_as:
            if len(self.results)>1:
                save_as = slugify(self.batch_title)
            else:
                save_as =  self.page.site.storageNode(self.results['#0']).cleanbasename
        outputFileNode=self.page.site.storageNode('user:output', 'pdf', save_as,autocreate=-1)
        zipped =  self.print_options.get('zipped')
        immediate_mode = self.batch_immediate
        if immediate_mode is True:
            immediate_mode = self.batch_parameters.get('immediate_mode')
        if immediate_mode and zipped:
            immediate_mode = 'download'
        if zipped:
            outputFileNode.path +='.zip'
            self.page.site.zipFiles(list(self.results.values()), outputFileNode)
        else:
            outputFileNode.path +='.pdf'
            self.pdf_handler.joinPdf(list(self.results.values()), outputFileNode)
        self.fileurl = outputFileNode.url(nocache=True, download=True)
        inlineurl = outputFileNode.url(nocache=True)
        resultAttr['url'] = self.fileurl
        resultAttr['document_name'] = save_as
        resultAttr['url_print'] = 'javascript:genro.openWindow("%s","%s");' %(inlineurl,save_as)
        if immediate_mode:
            resultAttr['autoDestroy'] = 600
        if immediate_mode=='print':
            self.page.setInClientData(path='gnr.clientprint',value=inlineurl,fired=True)
        elif immediate_mode=='download':
            self.page.setInClientData(path='gnr.downloadurl',value=inlineurl,fired=True)

    def table_script_option_pane(self, pane,print_modes=None, mail_modes=None,**kwargs):
        frame = pane.framePane(height='220px',width='400px')
        frame.dataFormula('#table_script_runner.dialog_options.title','dlgtitle',dlgtitle='!!Print Options',_onBuilt=True)
        frame.data('.print_mode',print_modes[0])
        frame.top.slotToolbar('*,stackButtons,*',stackButtons_font_size='.9em')
        sc = frame.center.stackContainer(selectedPage='^.print_mode')
        for pm in print_modes:
            if pm in mail_modes:
                if not (self.current_batch.mail_tags \
                    and self.application.checkResourcePermission(self.current_batch.mail_tags,self.userTags)):
                    continue
            getattr(self,'table_script_options_%s' %pm)(sc.contentPane(title=pm,pageName=pm,datapath='.%s' %pm),**kwargs)
            
    def table_script_option_common(self,fb,askLetterhead=None,**kwargs):
        if askLetterhead:
            fb.dbSelect(dbtable='adm.htmltemplate', value='^.letterhead_id',
                    lbl='!!Letterhead',hasDownArrow=True)
        fb.simpleTextArea(value='^#table_script_runner.data.batch_note',colspan=5,lbl='!!Notes',height='20px',lbl_vertical_align='top')

    def table_script_options_server_print(self, pane,resource_name=None,**kwargs):
        pane.attributes.update(title='!!Server Print')
        fb = self.table_script_fboptions(pane)
        self.server_print_option_fb(fb, resource=resource_name)

    def table_script_options_pdf(self, pane,**kwargs):
        pane.attributes.update(title='!!Pdf')
        fb = self.table_script_fboptions(pane)
        self.table_script_option_common(fb,**kwargs)
        fb.data('.zipped', False)
        fb.textbox(value='^.save_as', lbl='!!File Name', width='100%')
        fb.checkbox(value='^.zipped', label='!!Zip folder')

    def table_script_options_mail_pdf(self, pane,**kwargs):
        pane.attributes.update(title='!!Pdf by email')
        fb = self.table_script_fboptions(pane)
        self.table_script_option_common(fb,**kwargs)
        fb.textbox(value='^.to_address', lbl='!!To')
        fb.textbox(value='^.cc_address', lbl='!!CC')
        fb.textbox(value='^.subject', lbl='!!Subject')
        fb.simpleTextArea(value='^.body', lbl='!!Body', height='5ex', lbl_vertical_align='top')

    def table_script_options_mail_deliver(self, pane,**kwargs):
        pane.attributes.update(title='!!Deliver mail')
        fb = self.table_script_fboptions(pane)
        self.table_script_option_common(fb,**kwargs)
        fb.textbox(value='^.cc_address', lbl='!!CC', width='100%')
        fb.textbox(value='^.subject', lbl='!!Subject', width='100%')
        fb.simpleTextArea(value='^.body', lbl='!!Body', height='8ex', lbl_vertical_align='top')

    def table_script_fboptions(self, pane, fld_width='100%', tdl_width='4em', **kwargs):
        return pane.div(padding='10px').formbuilder(cols=1, width='100%', tdl_width=tdl_width,
                                                                    border_spacing='4px', fld_width=fld_width)

    def table_script_option_footer(self,pane,**kwargs):
        bar = pane.slotBar('3,exturl,*,cancelbtn,3,confirmbtn,3',_class='slotbar_dialog_footer')
        bar.cancelbtn.slotButton('!!Cancel',action='FIRE .cancel;')
        bar.confirmbtn.slotButton('!!Print', action='FIRE .confirm;')
        self.table_script_extUrlButton(bar.exturl)
        return bar
        
    def table_script_parameters_footer(self,pane, immediate=None,**kwargs):
        if immediate:
            bar = pane.slotBar('3,exturl,*,cancelbtn,3,downloadbtn,3,printbtn,3',_class='slotbar_dialog_footer')
            bar.cancelbtn.slotButton('!!Cancel',action='FIRE .cancel;')
            bar.downloadbtn.slotButton('!!Download', action="""SET #table_script_runner.data.immediate_mode ="download";  
                                                               FIRE .confirm ="download";""")
            bar.printbtn.slotButton('!!Print', action="""SET #table_script_runner.data.immediate_mode ="print";  
                                                         FIRE .confirm ="print";""")
            if immediate=='print':
                bar.replaceSlots('downloadbtn,3','')
            elif immediate=='download':
                bar.replaceSlots('printbtn,3','')
        else:
            bar = pane.slotBar('3,exturl,*,cancelbtn,3,confirmbtn,3',_class='slotbar_dialog_footer')
            bar.cancelbtn.slotButton('!!Cancel',action='FIRE .cancel;')
            bar.confirmbtn.slotButton('!!Confirm', action='FIRE .confirm;')
        self.table_script_extUrlButton(bar.exturl)
        return bar

    def get_template(self,template_address):
        if not ':' in template_address:
            template_address = 'adm.userobject.data:%s' %template_address
        return self.page.loadTemplate(template_address,asSource=True)[0]


    def table_script_extUrlButton(self,pane,**kwargs):
        pane.slotButton('!!Export url',
                                action="""
                                let kw = {
                                    table:table,
                                    resource:resource,
                                    res_type:res_type,
                                    rpc:'print_res_data',
                                    selectionName:selectionName,
                                    selectedRowidx:selectedRowidx,
                                    export_name:export_name,
                                    export_mode:export_mode
                                };

                                data.getNodes().forEach(function(n){
                                    if(n.label=='batch_options'){
                                        return;
                                    }
                                    let v = n.getValue();
                                    if(!isNullOrBlank(v)){
                                        kw[n.label] = v
                                    }
                                });
                                for(let k in kw){
                                    kw[k] = asTypedTxt(kw[k])
                                }
                                let url = genro.makeUrl('/adm/endpoint',kw);
                                genro.textToClipboard(url,msg);
                               FIRE .cancel;
                                """,resource='=.#parent.resource',
                                    res_type='=.#parent.res_type',
                                    msg='!!Link in clipboard',
                                    table='=.#parent.table',
                                    data='=.#parent.data',
                                    selectedRowidx='=.#parent.selectedRowidx',
                                    selectionName='=.#parent.selectionName',
                                    export_mode='html',
                                    export_name='=.#parent.resource',
                                    ask=dict(title='!!Export url',
                                                fields=[dict(name='export_name',lbl='Name'),
                                                            dict(name='export_mode',lbl='Output',tag='filteringSelect',
                                                            values='xls,csv,html')])
                                    )

