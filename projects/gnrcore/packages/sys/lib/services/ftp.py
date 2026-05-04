
import os
import re

from datetime import datetime
from gnr.core import gnrstring
from gnr.core.gnrbag import Bag, DirectoryResolver, BagResolver
from gnr.lib.services import GnrBaseService
from gnr.core.gnrdecorator import public_method
from gnr.web.gnrbaseclasses import BaseComponent
from gnr.web.gnrwebstruct import struct_method

class SftpService(GnrBaseService):
    def __init__(self, parent=None,host=None,username=None,password=None,private_key=None,port=None):
        pass

    def __call__(self,host=None,username=None,password=None,private_key=None,port=None):
        pass

    def downloadFilesIntoFolder(self,sourcefiles=None,destfolder=None,
                                callback=None,preserve_mtime=None,thermo_wrapper=None,**kwargs):
        pass

    def uploadFilesIntoFolder(self,sourcefiles=None,destfolder=None,
                                callback=None,preserve_mtime=None,
                                thermo_wrapper=None,confirm=None,**kwargs):
        pass

    def sftpResolver(self,path=None,**kwargs):
        return SftpDirectoryResolver(path,_page=self.parent.currentPage,
                                        ftpservice=self.service_name,
                                        **kwargs)
    
        

class SftpDirectoryResolver(DirectoryResolver):
    classKwargs = {'cacheTime': 500,
                   'readOnly': True,
                   'invisible': False,
                   'relocate': '',
                   'ext': 'xml',
                   'include': '',
                   'exclude': '',
                   'callback': None,
                   'dropext': False,
                   'processors': None,
                   'ftpservice':None,
                   '_page':None
    }
    classArgs = ['path', 'relocate']
    
    def resolverSerialize(self):
        self._initKwargs.pop('_page')
        return BagResolver.resolverSerialize(self)
        
    def load(self):
        """TODO"""
        extensions = dict([((ext.split(':') + (ext.split(':'))))[0:2] for ext in self.ext.split(',')]) if self.ext else dict()
        extensions['directory'] = 'directory'
        result = Bag()
        ftp = self._page.getService(service_type='ftp',service_name=self.ftpservice)()
        try:
            directory = sorted(ftp.listdir(self.path) if self.path else ftp.listdir())
        except OSError:
            directory = []
        if not self.invisible:
            directory = [x for x in directory if not x.startswith('.')]
        for fname in directory:
            nodecaption = fname
            fullpath = os.path.join(self.path, fname) if self.path else fname
            relpath = os.path.join(self.relocate, fname)
            addIt = True
            if ftp.isdir(fullpath):
                ext = 'directory'
                if self.exclude:
                    addIt = gnrstring.filter(fname, exclude=self.exclude, wildcard='*')
            else:
                if self.include or self.exclude:
                    addIt = gnrstring.filter(fname, include=self.include, exclude=self.exclude, wildcard='*')
                fname, ext = os.path.splitext(fname)
                ext = ext[1:]
            if addIt:
                label = self.makeLabel(fname, ext)
                handler = getattr(self, 'processor_%s' % extensions.get(ext.lower(), None), None)
                if not handler:
                    processors = self.processors or {}
                    handler = processors.get(ext.lower(), self.processor_default)
                try:
                    stat = ftp.stat(fullpath)
                    mtime = datetime.fromtimestamp(stat.st_mtime)
                    atime = datetime.fromtimestamp(stat.st_atime)
                    #ctime = datetime.fromtimestamp(stat.st_ctime)
                    size = stat.st_size
                except OSError:
                    mtime = None   
                    #ctime = None  
                    atime = None                   
                    size = None
                caption = fname.replace('_',' ').strip()
                m=re.match(r'(\d+) (.*)',caption)
                caption = '!!%s %s' % (str(int(m.group(1))),m.group(2).capitalize()) if m else caption.capitalize()
                nodeattr = dict(file_name=fname, file_ext=ext, rel_path=relpath,
                               abs_path=fullpath, mtime=mtime, atime=atime, #ctime=ctime,
                                nodecaption=nodecaption,
                               caption=caption,size=size)
                if self.callback:
                    self.callback(nodeattr=nodeattr)
                result.setItem(label, handler(fullpath),**nodeattr)
        ftp.close()
        return result

    def processor_directory(self, path):
        """TODO
        
        :param path: TODO"""
        return SftpDirectoryResolver(path,  os.path.basename(path), 
                                    **self.instanceKwargs)
        


class SftpClient(BaseComponent):
    py_requires='public:Public'

    @struct_method
    def sftp_sftpClientLayout(self,pane,ftpname=None,
                            datapath='.sftpclient',destdir=None,remotedir=None,**kwargs):
        bc = pane.borderContainer(datapath=datapath,_anchor=True,**kwargs)
        self.sftp_remoteTree(bc.roundedGroupFrame(region='left',title='!!Remote',
                            datapath='.remote',width='50%',
                            splitter=True),ftpname=ftpname,remotedir=remotedir)
        self.sftp_localTree(bc.roundedGroupFrame(region='center',title='!!Local',
                            datapath='.local'),ftpname=ftpname,destdir=destdir)

    def sftp_remoteTree(self,frame,ftpname=None,remotedir=None):
        resolver = self.getService('ftp',ftpname).sftpResolver()
        frame.data('.tree',resolver())
        self.sftp_fileTree(frame,nodeId='%s_src' %ftpname,topic='%s_upload' %ftpname)
        frame.dataRpc(None,self.sftp_uploadFiles,ftp=ftpname,
                    _onResult="""kwargs._dropnode.refresh(true);""",
                    **{'subscribe_%s_upload' %ftpname:True})

    def sftp_localTree(self,frame,ftpname=None,destdir=None):
        resolver= DirectoryResolver(destdir or self.site.getStatic('site').path())
        frame.data('.tree',resolver())
        self.sftp_fileTree(frame,nodeId='%s_dest' %ftpname,
                            topic='%s_download' %ftpname)
        frame.dataRpc(None,self.sftp_downloadFiles,ftp=ftpname,
                    _onResult="""kwargs._dropnode.refresh(true);""",
                        **{'subscribe_%s_download' %ftpname:True})


    def sftp_onDrag(self):
        return """var children=treeItem.getValue('static')
                  if(!children){
                      dragValues['fsource']=[treeItem.attr.abs_path];
                      return
                  }
                   result=[];
                   children.forEach(function(n){
                        if (n.attr.checked && !n._value){result.push(n.attr.abs_path);
                    }},'static');
                   dragValues['fsource']= result; 
               """

    @public_method
    def sftp_downloadFiles(self,sourcefiles=None,destfolder=None,ftp=None,**kwargs):
        self.getService('ftp',ftp).downloadFilesIntoFolder(sourcefiles=sourcefiles,
                                                destfolder=destfolder,**kwargs)

    @public_method
    def sftp_uploadFiles(self,sourcefiles=None,destfolder=None,ftp=None,**kwargs):
        self.getService('ftp',ftp).uploadFilesIntoFolder(sourcefiles=sourcefiles,
                                                destfolder=destfolder,**kwargs)


    def sftp_fileTree(self,pane,topic=None,**kwargs):
        tree = pane.treeGrid(storepath='.tree',hideValues=True, 
                      selectedLabelClass='selectedTreeNode',
                      selected_abs_path='.abs_path',selected_file_ext='.file_ext',
                      checked_abs_path='.checked_abs_path',
                      #labelAttribute='nodecaption',
                       autoCollapse=True,
                      onDrag_fsource=self.sftp_onDrag(),
                      headers=True,draggable=True,dragClass='draggedItem',
                      onDrop_fsource="""
                         if(dropInfo.treeItem.attr.file_ext!='directory'){
                             return false;
                         }else{
                             genro.publish('%s',{
                                destfolder:dropInfo.treeItem.attr.abs_path,
                                _dropnode:dropInfo.treeItem,
                                sourcefiles:data});
                         }
                     """ %topic,dropTargetCb_fsource="""
                     if(dropInfo.selfdrop || dropInfo.treeItem.attr.file_ext!='directory'){
                         return false;
                     }
                     return true;
                     """,**kwargs)
        tree.column('nodecaption',header='!!Name')
        tree.column('file_ext',size=50,header='!!Ext')
        tree.column('size',header='!!Size(KB)',size=60,dtype='L')
        tree.column('mtime',header='!!MTime',size=100,dtype='DH')
