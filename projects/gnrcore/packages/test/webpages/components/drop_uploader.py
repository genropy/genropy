# -*- coding: utf-8 -*-

"""DropUploader: every way of getting a file from the browser to the server

The area covers the drop targets (dropUploader, dropFileFrame, dropFileGrid),
the modal dialogs (modalUploaderDialog, multiUploaderDialog, modalUploader as a
widget) and the in-place editors that upload the image or document they show.
What changes between them is where the file lands and what runs afterwards:
an onUploaded_<nodeId> method, an onUploadedMethod callback, or a javascript
onResult.
"""

import os

from gnr.core.flatfiles import XlsReader
from gnr.core.gnrbag import Bag, DirectoryResolver
from gnr.core.gnrdecorator import public_method


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
        """modalUploaderDialog: open the uploader from javascript

        The destination path is typed in the textbox and handed to the dialog,
        so the caller decides at click time where the file goes.
        """
        fb = pane.formbuilder()
        fb.textbox(value='^.testpath',lbl='Destpath')
        fb.button('Test').dataController(
            "genro.dlg.modalUploaderDialog('test',{destpath:destpath,_sourceNode:this})",
            destpath='=.testpath'
        )

    def test_10_modalUploader_2(self, pane):
        """modalUploaderDialog with onConfirm: show what was just uploaded

        The file always lands on the same site path, and the onConfirm handler
        reloads the iframe with a cache-busting parameter — otherwise the
        browser would keep showing the previous version of the document.
        """
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
        """modalUploader as a widget: an upload box inside a form

        Same dialog as the previous case, but embedded as a form field: the
        widget shows the current document, dest_stn says where the upload goes
        and value receives the resulting path.
        """
        box = pane.formbuilder(cols=2)
        box.modalUploader(height='210px',width='190px',border='1px solid silver',
                           margin='10px',rounded=8,
                           value='^.destinazione',
                           dest_stn='site:ca_fronte.pdf',
                           label='Carta di identità fronte')
        box.textbox(value='^.destinazione')

    @public_method
    def onUploaded_test_uploader(self, file_url=None, file_path=None, file_ext=None, pippo=None,
                                  action_results=None, **kwargs):
        """Callback found by convention from the uploader nodeId (test_0)"""
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
        """onUploadedMethod of test_1: report size, path and url back to the client"""
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
        """Subscriber of test_2: move every queued file into the chosen user's folder"""
        sn = self.db.application.site.storageNode('site:import_queue')
        for node in sn.children():
            node.move('site:files/{user}/'.format(user=user_id))
            print('FILE MOVED: ', node.internal_path)

    def test_3_imgUploaderEdit(self, pane):
        """Editable img: upload the picture the tag is showing

        With edit=True the img becomes its own uploader: the file is stored
        under upload_folder with the name coming from upload_filename, so
        changing the identifier above changes the destination. crop_height and
        crop_width fix the visible frame regardless of the picture's size.

        todo: the placeholder points at an apple.com url that no longer exists;
        replace it with an asset served by the instance.
        """
        bc = pane.borderContainer(height='500px')
        top = bc.contentPane(region='top')
        fb = top.formbuilder(cols=1)

        fb.textbox(value='^.id',lbl='Image identifier')
        fb.textbox(value='^.avatar_url',lbl='Image url',width='50em')
        center = bc.contentPane(region='center')
        center.img(src='^.avatar_url',crop_height='200px',crop_width='250px',upload_folder='site:test/testimages',upload_filename='=.id',
                           border='1px solid silver',rounded=8,margin='10px',
                           placeholder='http://images.apple.com/euro/home/images/icloud_hero.png',
                           shadow='2px 2px 5px silver',edit=True,zoomWindow='ImageDeatail' )

    def test_4_embedUploaderReadOnly(self, pane):
        """embed with upload attributes but edit=False

        The same upload_folder/upload_filename pair works on embed, which
        renders documents rather than images; here edit=False, so the tag only
        displays what the previous test uploaded.
        """
        bc = pane.borderContainer(height='500px')
        top = bc.contentPane(region='top')
        fb = top.formbuilder(cols=1)

        fb.textbox(value='^.id',lbl='Image identifier')
        fb.textbox(value='^.avatar_url',lbl='Image url',width='50em')
        center = bc.contentPane(region='center')
        center.embed(src='^.avatar_url',height='100%',width='100%',upload_folder='site:test/testimages',upload_filename='=.id',
                           border='1px solid silver',rounded=8,margin='10px',
                           shadow='2px 2px 5px pink',edit=False,zoomWindow='ImageDeatail' )

    def test_5_dropFileGridXLS(self, pane):
        """dropFileGrid: upload spreadsheets and read them back

        Three panes, left to right: the drop grid that uploads into
        site:testuploader/foo_up, the list of the xls files found there, and
        the rows of the selected one. The last grid is built at runtime —
        rpc_xlsRows derives its struct from the spreadsheet headers.
        """
        bc = pane.borderContainer(height='400px')
        left = bc.borderContainer(region='left', width='40%', margin='5px')
        right = bc.borderContainer(region='right', width='40%', margin='5px')

        center = bc.borderContainer(region='center', margin='5px')

        def footer(footer, **kwargs):
            footer.button('Upload', action='PUBLISH foo_uploader_upload', float='right')

        self.dropFileGrid(left, uploaderId='foo_uploader', datapath='.uploader',
                          label='Upload here', enabled=True,
                          onResult='alert("Done"); FIRE test.test_5_dropFileGridXLS.update_loaded;',
                          metacol_description=dict(name='!!Description', width='10em'), footer=footer,
                          uploadPath='site:testuploader/foo_up',
                          preview=True, uploadedFilesGrid=True)

        pane.dataRpc('.loaded_content', 'getLoadedFiles', _fired='^.update_loaded',
                     uploadPath='site:testuploader/foo_up', _onStart=True)

        def struct(struct):
            r = struct.view().rows()
            r.cell('filename', name='Filename', width='10em')

        self.includedViewBox(center, label='!!loaded content',
                             datapath='test.test_5_dropFileGridXLS',
                             storepath='.loaded_content',
                             selected_filepath='.uploaded_filepath',
                             hiddencolumns='filepath',
                             struct=struct)
        pane.dataRpc('#xlsgrid.data', 'xlsRows', docname='^.uploaded_filepath', _onResult='FIRE #xlsgrid.reload;')

        iv = self.includedViewBox(right, label='!!Xls Rows',
                                  nodeId='xlsgrid',
                                  datapath='test.test_5_dropFileGridXLS.xlsgrid',
                                  storepath='.data.store', structpath='.data.struct',
                                  autoWidth=True)
        iv.gridEditor()

    def rpc_xlsRows(self, docname=None):
        """Read the selected spreadsheet and return struct and rows in one Bag"""
        result = Bag()
        reader = XlsReader(docname)
        headers = reader.headers
        result['struct'] = self.newGridStruct()
        r = result['struct'].view().rows()
        for colname in headers:
            r.cell(colname, name=colname, width='5em')
        for i, row in enumerate(reader()):
            result.setItem('store.r_%i' % i, None, dict(row))
        return result

    def rpc_getLoadedFiles(self, uploadPath=None, **kwargs):
        """List the xls files currently sitting in the upload folder"""
        path = self.site.getStaticPath(uploadPath)
        result = Bag()
        b = DirectoryResolver(path)
        for i, n in enumerate(
                [(t[1], t[2]) for t in b.digest('#a.file_ext,#a.file_name,#a.abs_path') if t[0] == 'xls']):
            result.setItem('r_%i' % i, None, filename=n[0], filepath=n[1])
        return result

    def onUploading_foo_uploader(self, file_url=None, file_path=None,
                                 description=None, titolo=None, **kwargs):
        """Hook called while the file is being received, before it is stored"""
        result = dict(file_url=file_url, file_path=file_path)
        print(result)
        return result

    def test_6_dropFileFrame(self, pane):
        """dropFileFrame: the drop area and its file list in a single frame

        The lighter alternative to dropFileGrid when the page only needs a
        place to drop files: metacol_* declares the extra columns the user can
        fill in for each one.
        """
        pane.dropFileFrame(height='300px',rounded=6,border='1px solid gray',preview=True,
                            metacol_description=dict(name='!!Description', width='10em'))

    def test_7_multifileDlg(self, pane):
        """multiUploaderDialog with no ask step: straight to the upload path"""
        pane.button('test',action="genro.dlg.multiUploaderDialog('Carica fatture elettroniche',{uploadPath:uploadPath,onResult:function(res){genro.bp(true)}});",uploadPath='site:testupload')

    def test_8_movableImage(self, pane):
        """Drag the picture inside its frame with plain dojo events

        Not an uploader case: it comes from the same legacy page and shows how
        an img can be panned inside a clipped div by connecting to the raw
        dojo drag events and writing the offsets into the datastore.

        todo: the image url no longer resolves, so the frame renders empty;
        point it at an asset served by the instance.
        """
        pane.div(height='100px',width='150px',overflow='hidden').img(src='http://images.apple.com/euro/home/images/icloud_hero.png',
               margin_top='^.margin_top',margin_left='^.margin_left',
               onCreated="""
                  var that=this;
                  this._onDragImage=function(e){
                     var dx=this.s_x-e.clientX;
                 	 var dy=this.s_y-e.clientY;
                 	 that.s_x=e.clientX;
                      that.s_y=e.clientY;
                 	  var mt=GET .margin_top || '0px';
                      var ml=GET .margin_left || '0px';
                      SET .margin_top=(parseFloat(mt)-dy)+'px';
                      SET .margin_left=(parseFloat(ml)-dx)+'px';
                  };
                  dojo.connect(this.domNode,'ondragstart',function(e){
                        e.stopPropagation();
                        e.preventDefault();
                        that.s_x=e.clientX;
                        that.s_y=e.clientY;
                        var d=dojo.body();
                        d.style.cursor='move'
                        var c1= dojo.connect(d, "onmousemove",that,'_onDragImage');
			            var c2=dojo.connect(d, "onmouseup",  function(e){
			                d.style.cursor='auto'
                 	        dojo.disconnect(c1);
                 	        dojo.disconnect(c2);
                 	        });
                  });
               """)
