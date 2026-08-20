# -*- coding: utf-8 -*-

"""A folder of files as the store of a grid and of a linkedForm

`fsStore` fills a grid from a storage folder instead of from a table, so the
rows are files and their name, description and date are file metadata. The last
case puts a linkedForm on top of that store, which is what makes a plain folder
editable through the same form machinery a table gets. The sample folder is
`pkg:test/testdata/docstore`.
"""


class GnrCustomWebPage(object):
    py_requires="""gnrcomponents/testhandler:TestHandlerFull,
                   gnrcomponents/formhandler:FormHandler,
                   gnrcomponents/framegrid:FrameGrid"""


    def test_4_document_folder(self,pane):
        """The folders to read typed by hand, resolved server side by app.getFileSystemSelection"""
        fb = pane.formbuilder(cols=1,border_spacing='3px')
        fb.textbox('^.folders',lbl='Folders')
        fb.dataRpc('.store','app.getFileSystemSelection',folders='^.folders',columns='name,description,date',include='*.xml')

    def struct_doc(self,struct):
        """Grid structure shared by the cases: the name, description and date of each file"""
        r = struct.view().rows()
        r.cell('name',width='10em',name='!!Name')
        r.cell('description',width='20em',name='!!Description')
        r.cell('date',dtype='D',width='5em',name='!!Date')

    def test_2_document_view(self,pane):
        """frameGrid whose rows come from fsStore over the docstore folder"""
        frame = pane.borderContainer(height='400px').frameGrid(frameCode='test2',struct=self.struct_doc,
                                    autoToolbar=False,
                                    region='center',
                                    datapath='.view')
        frame.grid.fsStore(childname='store',folders='pkg:test/testdata/docstore',_onStart=True,_fired='^.reload')

    def test_3_document_collection_form(self,pane):
        """The same fsStore grid plus a linkedForm opening one file in a dialog on double click"""
        view = pane.borderContainer(height='400px').frameGrid(frameCode='test3',struct=self.struct_doc,
                                    autoToolbar=False,
                                    region='center',
                                    datapath='.view')
        view.grid.fsStore(childname='store',folders='pkg:test/testdata/docstore',_onStart=True,_fired='^.reload')
        form = view.grid.linkedForm(frameCode='F_documents' ,
                                 datapath='.form',loadEvent='onRowDblClick',
                                 dialog_height='450px',dialog_width='620px',
                                 dialog_title='Ticket',
                                 handlerType='dialog',
                                 childname='form',attachTo=pane,
                                 store='document')
        self.doc_form(form)

    def doc_form(self,form):
        """The dialog form of test_3: the three file attributes plus the standard toolbar"""
        form.top.slotToolbar('2,navigation,*,delete,add,save,semaphore,locker,2')
        fb = form.record.formbuilder(cols=1,border_spacing='3px')
        fb.textbox(value='^.name',lbl='Code')
        fb.textbox(value='^.description',lbl='Description')
        fb.dateTextBox(value='^.date',lbl='Date')



        
        
