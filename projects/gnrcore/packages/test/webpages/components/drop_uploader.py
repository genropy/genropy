# -*- coding: utf-8 -*-

"""DropUploader"""

from gnr.core.gnrbag import Bag, DirectoryResolver
from gnr.core.gnrdecorator import public_method
import os

class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                        gnrcomponents/drop_uploader"""

    def test_0_dropUploader(self, pane):
        "DropUploader: use of external to trigger an action once uploaded. Check print on console"
        pane.data('.pippo','42')
        pane.dropUploader(nodeId="test_uploader", external_pippo='^.pippo',
                            height = '100px', width='400px',
                            label= 'Drop file here or double click')
        
    def test_9_modalUploader(self, pane):
        fb = pane.formbuilder()
        fb.textbox(value='^.testpath',lbl='Destpath')
        fb.button('Test').dataController(
            "genro.dlg.modalUploaderDialog('test',{destpath:destpath,_sourceNode:this})",
            destpath='=.testpath'
        )

    def test_10_modalUploader_2(self, pane):
        pane.iframe(src='^.curr_url',height='210px',width='190px',border='1px solid silver')
        pane.button('Upload').dataController(
            """genro.dlg.modalUploaderDialog('test',{destpath:destpath,
                                            onConfirm:onConfirm},
                                            this)""",
            destpath='site:modalUploader_2.pdf',
            onConfirm = """PUT .curr_url = null;
                            SET .curr_url = genro.addParamsToUrl("/"+destpath,{_nocache:genro.time36Id()});"""
        )

    def test_11_modalUploader_3(self, pane):
        box = pane.formbuilder(cols=2)
        box.modalUploader(height='210px',width='190px',border='1px solid silver',
                           margin='10px',rounded=8,
                           value='^.destinazione',
                           label='Carta di identità fronte')
        box.data('.destinazione','site:ca_fronte.pdf')
        box.textbox(value='^.destinazione')
        
       # box.modalUploader(height='210px',width='190px',border='1px solid silver',
       #                    margin='10px',rounded=8,
       #                    value='site:ca_retro.pdf',
       #                    label='Carta di identità retro')
        


    @public_method
    def onUploaded_test_uploader(self, file_url=None, file_path=None, file_ext=None, pippo=None,
                                  action_results=None, **kwargs):
        print(pippo)
        print(file_path)

    def test_1_dropUploaderWithMethod(self, pane):
        "It's possible to define onUploading and onUploaded actions to manage file during upload procedure"
        fb = pane.formbuilder(cols=1, colswidth='100%')
        fb.div(hidden='^.file_path?=#v', lbl='File').dropUploader(height='100px', width='320px',
                            label="<div style='padding:20px'>Drop document here <br>or double click</div>",
                            uploadPath='site:files',
                            progressBar=True,
                            ask=dict(title='Prova',fields=[dict(name='message',lbl='Message')]),
                            onUploadedMethod=self.uploadFile)
        fb.textbox('^.size', lbl='Size (kB)', readOnly=True, hidden='^.file_path?=!#v')
        fb.textbox('^.file_path', lbl='File path', readOnly=True, hidden='^.file_path?=!#v', width='100%')
        fb.textbox('^.file_url', lbl='File url', readOnly=True, hidden='^.file_path?=!#v', width='100%')

    @public_method
    def uploadFile(self, file_path=None, **kwargs):
        fileSn = self.site.storageNode(file_path)
        file_url = fileSn.url()
        fullpath = fileSn.internal_path
        file_size = os.path.getsize(fullpath) / 1024 
        self.setInClientData(value=file_size, path='test.test_1_dropUploaderWithMethod.size')
        self.setInClientData(value=fullpath, path='test.test_1_dropUploaderWithMethod.file_path')
        self.setInClientData(value=file_url, path='test.test_1_dropUploaderWithMethod.file_url')
        self.clientPublish('floating_message', message=kwargs.get('message') or 'Upload completed')  

    def test_2_multiUploaderDialog(self, pane):
        """Through multiUploaderDialog it's possible to customize behaviour directly in javascript.
            Check instances/.../site/files/user_id folder for uploaded files"""
        uploader = pane.button('Upload more files')
        uploader.dataController("""
                                genro.dlg.multiUploaderDialog('!![en]Upload many files and assign them to users',{
                                            uploadPath:uploadPath,
                                            onResult:function(){
                                                genro.publish("floating_message",{message:"Upload completato", messageType:"message"});
                                                genro.publish('trigger_action',{user_id:user_id}); }
                                            });""", 
                                            uploadPath=':import_queue', 
                                            _ask=dict(title='Choose users to whom to assign files', 
                                                fields=[dict(name='user_id', lbl='User', tag='dbselect', table='adm.user')]))

        pane.dataRpc(self.triggerAnAction, subscribe_trigger_action=True)
        
    @public_method
    def triggerAnAction(self, user_id=None, category=None, **kwargs):
        sn = self.db.application.site.storageNode('site:import_queue')
        for node in sn.children():
            node.move('site:files/{user}/'.format(user=user_id))
            print('FILE MOVED: ', node.internal_path)

    