#-*- coding: utf-8 -*-
#--------------------------------------------------------------------------
# package           : GenroPy web - see LICENSE for details
# module gnrwebcore : core module for genropy web framework
# Copyright (c)     : 2004 - 2022 Softwell srl - Milano 
# Written by    : Giovanni Porcari, Michele Bertoldi
#                 Saverio Porcari, Francesco Porcari 
#--------------------------------------------------------------------------
#This library is free software; you can redistribute it and/or
#modify it under the terms of the GNU Lesser General Public
#License as published by the Free Software Foundation; either
#version 2.1 of the License, or (at your option) any later version.

#This library is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
#Lesser General Public License for more details.

#You should have received a copy of the GNU Lesser General Public
#License along with this library; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

#Copyright (c) 2022 Softwell. All rights reserved.

from email.mime import application
from genericpath import isdir
import os
import urllib.parse
from attr import attrib, attributes
from gnr.core.gnrstructures import  GnrStructData
from gnr.core.gnrlang import getUuid,gnrImport,instanceMixin
from gnr.core.gnrdict import dictExtract
from gnr.core.gnrbag import Bag,BagResolver
from gnr.core.gnrlang import objectExtract
from gnr.core.gnrstring import slugify

class BaseMenu(object):
    def __init__(self,page) -> None:
        self.page = page
        self.db = self.page.db
        self.application = self.db.application

class MenuStruct(GnrStructData):
    def __init__(self,filepath=None,branchMethod=None,page=None,**kwargs):
        super().__init__()
        self.setBackRef()
        self.branchMethod = branchMethod
        filepath,ext = self._handleFilepath(filepath)
        if not filepath:
            return
        getattr(self,f'_handle_{ext[1:]}')(filepath,page=page,**kwargs)

    def _getBranchMethod(self,page,obj):
        if self.branchMethod:
            return self.branchMethod
        for methodname in dir(obj):
            if methodname.startswith('config_'):
                handler = getattr(obj,methodname)
                group_code = getattr(handler,'group_code',None)
                if group_code==page.rootenv['user_group_code']:
                    return methodname
        return 'config'

        
    def _handle_py(self,filepath,page=None,**kwargs):
        m = gnrImport(filepath, avoidDup=True)
        mixinclass = getattr(m,'Menu',None)
        if mixinclass:
            menuinstance = BaseMenu(page)
            instanceMixin(menuinstance,mixinclass)
            getattr(menuinstance,self._getBranchMethod(page,menuinstance))(self,**kwargs)
        else:
            getattr(m,self._getBranchMethod(page,m))(self,application=page.application, **kwargs)
            autoconvert = page.application.getPreference('autoconvert_legacy_menu',pkg='sys') or False
            if autoconvert and len([k for k in dir(m) if not k.startswith('__')])==1:
                self.toPython(filepath)

  
    def _handle_xml(self,filepath,page=None,**kwargs):
        self.fillFrom(filepath)
        autoconvert = page.application.getPreference('autoconvert_legacy_menu',pkg='sys') or False

        if len(self) and autoconvert:
            self.toPython(filepath.replace('.xml','.py'))

    def _handleFilepath(self,filepath):
        if not filepath:
            return None,None
        filename,ext = os.path.splitext(filepath)
        if not ext:
            if os.path.exists(f'{filepath}.xml'):
                filepath = f'{filepath}.xml'
                ext = '.xml'
            elif os.path.exists(f'{filepath}.py'):
                filepath = f'{filepath}.py'
                ext = '.py'
            else:
                return None,None
        return filepath,ext
    
    
    def branch(self, label, basepath=None ,tags='',pkg=None,**kwargs):
        return self.child('branch',label=label,basepath=basepath,tags=tags,pkg=pkg,**kwargs)
    
    def webpage(self, label,filepath=None,tags='',multipage=None, **kwargs):
        return self.child('webpage',label=label,multipage=multipage,tags=tags,
                        filepath=filepath,_returnStruct=False,**kwargs)

    def thpage(self, label=None,table=None,tags='',multipage=None, **kwargs):
        return self.child('thpage',label=label,table=table,
                            multipage=multipage,tags=tags,_returnStruct=False,**kwargs)

    def lookups(self,label=None,lookup_manager=None,tags=None,**kwargs):
        return self.child('lookups',label=label,lookup_manager=lookup_manager,
                    tags=tags,_returnStruct=False,**kwargs)
    
    def lookupPage(self,label=None,table=None,tags=None,**kwargs):
        return self.child('lookupPage',label=label,table=table,
                    tags=tags,_returnStruct=False,**kwargs)

    def lookupBranch(self,label=None,pkg=None,tables=None,tags=None,**kwargs):
        return self.child('lookupBranch',label=label,pkg=pkg,tables=tables,
                            tags=tags,_returnStruct=False,**kwargs)
    
    def directoryBranch(self,label=None,pkg=None,folder=None,tags=None,**kwargs):
        return self.child('directoryBranch',label=label,pkg=pkg,folder=folder,
                            tags=tags,_returnStruct=False,**kwargs)

    def dashboardBranch(self,label,dashboard=None,tags=None,cacheTime=None,**kwargs):
        return self.child('dashboardBranch',label=label,dashboard=dashboard,
                            tags=tags,cacheTime=cacheTime,_returnStruct=False,**kwargs)


    def packageBranch(self,label=None,pkg=None,**kwargs):
        return self.child('packageBranch',label=label,pkg=pkg,_returnStruct=False,**kwargs)

    
    def tableBranch(self,label=None,table=None,**kwargs):
        return self.child('tableBranch',label=label,table=table,_returnStruct=False,**kwargs)


    def toPython(self,filepath=None):
        filepath = filepath or 'menu.py'
        with open(filepath,'w') as f:
            text = """# encoding: utf-8
class Menu(object):
    def config(self,root,**kwargs):"""         
            f.write(text)
            self._toPythonInner(f,self,'root')


    def _toPythonInner(self,filehandle,b,rootname):
        filehandle.write('\n')
        for n in b:
            kw = dict(n.attr)
            kw.pop('tag',None)
            label = kw.pop('label',n.label)
            attrlist = ['u"%s"' %label]
            for k,v in list(kw.items()):
                if k=='file':
                    k = 'filepath'
                attrlist.append('%s="%s"' %(k,v))
            if n.value:
                varname = slugify(label).replace('!!','').replace('-','_')
                filehandle.write('        %s = %s.branch(%s)' %(varname,rootname,', '.join(attrlist)))
                self._toPythonInner(filehandle,n.value,varname) 
            elif 'table' in kw:
                filehandle.write('        %s.thpage(%s)' %(rootname,', '.join(attrlist)))
            elif 'lookup_manager' in kw:
                filehandle.write('        %s.lookups(%s)' %(rootname,', '.join(attrlist)))
            elif 'pkg' in kw:
                filehandle.write('        %s.branch(%s)' %(rootname,', '.join(attrlist)))
            else:
                filehandle.write('        %s.webpage(%s)' %(rootname,', '.join(attrlist)))
            filehandle.write('\n')

class NotAllowedException(Exception):
    pass

class MenuResolver(BagResolver):
    classKwargs = {'cacheTime': -1,
                   'readOnly': False,
                   'path': None,
                   'pkg':None,
                   'branchMethod':None,
                   'xmlresolved':True,
                   'aux_instance':None,
                   'basepath':None,
                   'level_offset':0,
                   'externalSite':None,
                   '_page':None}
    classArgs = ['path']

    def resolverSerialize(self):
        attr = super(MenuResolver, self).resolverSerialize()
        attr['kwargs'].pop('_page',None)
        return attr

    @property
    def app(self):
        return self._page.application


    def pkgMenu(self,pkgId,branchMethod=None,**kwargs):
        pkg = self.getPkg(pkgId)
        if not pkg:
            return
        pkgMenu = MenuStruct(os.path.join(pkg.packageFolder, 'menu'),
                                branchMethod=branchMethod,
                                page=self._page,
                                **kwargs)
        for pluginname,plugin in list(pkg.plugins.items()):
            pluginmenu = os.path.join(plugin.pluginFolder,'menu')
            if os.path.exists(pluginmenu):
                pkgMenu.update(MenuStruct(pluginmenu,page=self._page))
        return pkgMenu

    def getPkg(self,pkgId):
        return self.app.packages[pkgId]


    def getInstanceMenu(self):
        #legacy
        menuinstance = os.path.join(self.app.instanceFolder, 'menu.py')
        if os.path.exists(menuinstance):
            return MenuStruct(menuinstance,page=self._page)


    @property
    def indexMenu(self):
        instanceMenu = self.getInstanceMenu()
        if instanceMenu:
            return instanceMenu
        pkgMenus = self.app.config['menu?package']
        if pkgMenus:
            return self.legacyMenuFromPkgList(pkgMenus)
        result = self.pkgMenu(self._page.package.name)
        if len(result) == 1:
            result = result['#0']
        return result

    def legacyMenuFromPkgList(self,pkgMenus):
        pkgMenus = pkgMenus.split(',') if pkgMenus!='*' else list(self.app.packages.keys())
        if len(pkgMenus)==1:
            return self.pkgMenu(pkgMenus[0])
        else:
            result = MenuStruct()
            pkgMenuBag = None
            for pkgid in pkgMenus:
                pkgMenuBag = self.pkgMenu(pkgid)
                if not pkgMenuBag:
                    continue
                pkgattrs = self.getPkg(pkgid).attributes
                menu_label =pkgattrs.get('menu_label') or pkgattrs.get('name_long', pkgid)
                result.packageBranch(menu_label,pkg=pkgid)
            if len(result)==1:
                result = pkgMenuBag
        return result

    @property
    def sourceBag(self):
        if self.pkg:
            return self.pkgMenu(self.pkg,branchMethod=self.branchMethod,
                                **dictExtract(self.kwargs,'branch_'))
        return self.indexMenu


    def load(self):
        result = Bag()
        source = self.sourceBag[self.path]
        for node in source:
            if not self.allowedNode(node):
                continue
            warning = self.checkLegacyNode(node)
            if warning:
                self._page.log(f'AppMenu Changed tag in node {self.path}.{node.label}: {warning}')
            handler = getattr(self,f'nodeType_{node.attr["tag"]}')
            try:
                value,attributes = handler(node)
            except NotAllowedException:
                continue
            self.setLabelClass(attributes)
            result.setItem(node.label, value, attributes)
        return result

    def setLabelClass(self,attributes):
        labelClass = f'menu_shape menu_level_{self.level}'
        customLabelClass = attributes.get('customLabelClass')
        subtab = attributes.get('subtab')
        isDir = attributes.get('isDir')
        branchPage = attributes.get('branchPage')
        if customLabelClass:
            labelClass = f'{labelClass} {customLabelClass}'
        if attributes.get('workInProgress'):
            labelClass = f'{labelClass} workInProgress'
        if subtab:
            labelClass = f'{labelClass} menu_subtab'
        if isDir:
            labelClass = f'{labelClass} menu_branch'
        if branchPage:
            labelClass = f'{labelClass} branchPage'

        attributes['labelClass'] = labelClass

    @property
    def starturl(self):
        if not hasattr(self,'_starturl'):
            starturl = self._page.site.default_uri or '/'
            dbstore = self._page.dbstore
            if dbstore:
                starturl = f'{starturl}/{dbstore}'
            self._starturl = starturl
        return self._starturl


    def checkLegacyNode(self,node):
        nodeattr = node.attr
        nodeTag = nodeattr.get('tag')
        if nodeTag == 'branch':
            if nodeattr.get('dashboard'):
                nodeattr['tag'] = 'dashboardBranch'
                return 'updateToDashboardBranch'
            if nodeattr.get('dir'):
                nodeattr['tag'] = 'directoryBranch'
                nodeattr['folder'] = nodeattr.pop('dir')
                return 'updateToDirectoryBranch'
            if nodeattr.get('pkg'):
                nodeattr['tag'] = 'packageBranch'
                return 'updateToPackageBranch'

        if nodeTag=='webpage' and nodeattr.get('table'):
            nodeattr['tag'] = 'thpage'
            return 'thpage'
        if nodeTag=='thpage' and nodeattr.get('filepath'):
            nodeattr['tag'] = 'webpage'

        if nodeTag == 'lookups':
            lookup_manager = nodeattr.pop('lookup_manager',None)
            if lookup_manager is True:
                nodeattr['tag'] = 'lookupBranch'
                nodeattr['pkg'] = '*'
            else:
                table = nodeattr.get('table')
                pkg = nodeattr.get('pkg')
                lookup_manager = lookup_manager or table or pkg
                lookup_manager_list = lookup_manager.split('.')
                if len(lookup_manager_list)==2:
                    nodeattr['tag'] = 'lookupPage'
                    nodeattr['table'] = lookup_manager
                else:
                    nodeattr['tag'] = 'lookupBranch'
                    nodeattr['pkg'] = lookup_manager
    @property
    def level(self):
        level = len(self.path.split('.')) if self.path else 0
        if self.level_offset:
            return self.level_offset+level+1
        return level

    def allowedNode(self,node):
        nodeattr = node.attr
        auth_tags = nodeattr.get('tags')
        checkInstance = nodeattr.get('checkInstance')
        if checkInstance and self.app.instanceName not in checkInstance.split(','):
            return False
        if auth_tags and \
            not self.app.checkResourcePermission(auth_tags, self._page.userTags):
            return False
        multidb = nodeattr.get('multidb')
        dbstore = self._page.dbstore
        if (multidb=='slave' and not dbstore) or (multidb=='master' and dbstore):
            return False
        checkenv = nodeattr.get('checkenv')
        if checkenv and not self._page.rootenv[checkenv]:
            return False
        if not self.app.allowedByPreference(**nodeattr):
            return False
        return True

    def addParametersToUrl(self,url,externalSite=None,**kwargs):
        if 'dbstore' not in kwargs and self._page.dbstore and not kwargs.get('aux_instance'):
            kwargs['dbstore'] = self._page.dbstore
        if externalSite:
            externalSite = self._page.site.config['externalSites'].getAttr(externalSite)['url']
            url = f'{externalSite}{url}'

        return '?'.join((url,urllib.parse.urlencode({k:v for k,v in kwargs.items() if v is not None})))

    def nodeType_lookups(self,node):
        attributes = dict(node.attr)
        return None,attributes

    def checkExternalSite(self,attributes):
        externalSite = attributes.get('externalSite') or self.externalSite
        if externalSite:
            externalSite = self._page.site.config['externalSites'].getAttr(externalSite)['url']
            attributes['webpage'] = f"{externalSite}{attributes['webpage']}"

    def nodeType_webpage(self,node):
        attributes = dict(node.attr)
        if not self._page.checkPermission(attributes['filepath']):
            raise NotAllowedException('Not allowed page')
        aux_instance = attributes.get('aux_instance') or self.aux_instance
        attributes['webpage'] = attributes['filepath']
        attributes['url_aux_instance'] = aux_instance
        self.checkExternalSite(attributes)
        return None,attributes

    def nodeType_lookupBranch(self,node):
        attributes = dict(node.attr)
        attributes['isDir'] = True
        attributes['branchIdentifier'] = getUuid()
        kwargs = dict(attributes)
        kwargs.pop('tag')
        return LookupBranchResolver(level_offset=self.level,
                                aux_instance=attributes.get('aux_instance') or self.aux_instance,
                                externalSite= attributes.get('externalSite') or self.externalSite,
                                _page=self._page,**kwargs),attributes

    def nodeType_lookupPage(self,node):
        attributes = dict(node.attr)
        table = attributes.get('table') 
        attributes.setdefault('multipage',False)
        attributes['webpage'] = '/sys/lookup_page'
        if table:
            attributes['webpage'] = f"/sys/lookup_page/{table.replace('.','/')}"
        else:
            table = attributes['start_table']
        viewResource = attributes.pop('viewResource',None)
        if viewResource:
            attributes['url_viewResource'] = viewResource
        aux_instance = attributes.pop('aux_instance',None) or self.aux_instance
        attributes['url_aux_instance'] = aux_instance
        attributes['url_th_from_package'] = attributes.get('pkg_menu')
        self.checkExternalSite(attributes)
        if not aux_instance:
            attributes['url_th_from_package'] = attributes['url_th_from_package'] or self._page.package.name
        attributes.setdefault('multipage',False)
        tableattr = self._page.db.table(table).attributes
        attributes['label'] =  attributes.get('label') or tableattr.get('name_long')
        application = self.app.getAuxInstance(aux_instance) if aux_instance else self.app
        if not application.allowedByPreference(**tableattr):
            raise NotAllowedException('Not allowed by preference')
        return None,attributes

    def nodeType_thpage(self,node):
        attributes = dict(node.attr)
        table = attributes['table']
        attributes['webpage'] = f'/sys/thpage/{table.replace(".","/")}'
        for k in ('pkey','pageResource','formResource','viewResource'):
            v = attributes.pop(k,None)
            if v is not None:
                attributes[f'url_th_{k}'] = v
        aux_instance = attributes.pop('aux_instance',None) or self.aux_instance
        attributes['url_aux_instance'] = aux_instance
        attributes['url_th_from_package'] = attributes.get('pkg_menu')
        self.checkExternalSite(attributes)
        if not aux_instance:
            attributes['url_th_from_package'] = attributes['url_th_from_package'] or self._page.package.name
        pkey = attributes.get('url_th_pkey') or attributes.get('start_pkey')
        if pkey:
            attributes.setdefault('multipage',False)
            attributes.setdefault('url_single_record',True)
            attributes.setdefault('url_th_public',True)
        else:
            attributes.setdefault('multipage',True)
        tableattr = self._page.db.table(table).attributes
        attributes['label'] =  attributes.get('label') or tableattr.get('name_long')
        application = self.app.getAuxInstance(aux_instance) if aux_instance else self.app
        if not application.allowedByPreference(**tableattr):
            raise NotAllowedException('Not allowed by preference')
        return None,attributes
    



    def nodeType_dashboardBranch(self,node):
        attributes = dict(node.attr)
        attributes['isDir'] = True
        return PackageMenuResolver(pkg=attributes['pkg'],level_offset=self.level,
                                branchMethod='dashboardBranch',
                                aux_instance=attributes.get('aux_instance') or self.aux_instance,
                                externalSite= attributes.get('externalSite') or self.externalSite,
                                _page=self._page,**dictExtract(attributes,'branch_')),attributes


    def nodeType_directoryBranch(self,node):
        attributes = dict(node.attr)
        attributes['isDir'] = True
        return DirectoryMenuResolver(level_offset=self.level,
                                pkg=attributes.get('pkg') or self.pkg,
                                folder = attributes.get('folder'),
                                aux_instance=attributes.get('aux_instance') or self.aux_instance,
                                externalSite= attributes.get('externalSite') or self.externalSite,
                                _page=self._page),attributes

    def nodeType_tableBranch(self,node):
        attributes = dict(node.attr)
        attributes['branchIdentifier'] = getUuid()
        kwargs = dict(attributes)
        kwargs.pop('tag')
        cacheTime = kwargs.pop('cacheTime',None)
        xmlresolved = kwargs.pop('resolved',False)
        sbresolver = TableMenuResolver(xmlresolved=xmlresolved,
                            _page=self._page,cacheTime=cacheTime, 
                            level_offset=self.level,
                            **kwargs)
        attributes['isDir'] = True
        return sbresolver,attributes

    def nodeType_packageBranch(self,node):
        attributes = dict(node.attr)
        value = self.pkgMenu(attributes['pkg'],branchMethod=attributes.get('branchMethod'),
                                **dictExtract(attributes,'branch_'))
        path = None
        if not value:
            return None,attributes
        if len(value) == 1:
            path = '#0'
        attributes['isDir'] = True
        return PackageMenuResolver(path=path,pkg=attributes['pkg'],level_offset=self.level,
                                branchMethod=attributes.get('branchMethod'),
                                aux_instance=attributes.get('aux_instance') or self.aux_instance,
                                externalSite= attributes.get('externalSite') or self.externalSite,
                                _page=self._page,**dictExtract(attributes,'branch_')),attributes


    def nodeType_branch(self,node):
        attributes = dict(node.attr)
        basepath = attributes.get('basepath')
        attributes['isDir'] = True
        attributes['child_count'] = len(node.value)
        if self.basepath:
            basepath = f'{self.basepath}/{basepath}' if basepath else self.basepath
        path = f'{self.path}.{node.label}' if self.path else node.label
        menuRes = MenuResolver(path=path,basepath=basepath,pkg=self.pkg,
                        aux_instance=attributes.get('aux_instance') or self.aux_instance,
                        externalSite=attributes.get('externalSite') or self.externalSite,
                        _page=self._page)
        return menuRes,attributes


class TableMenuResolver(MenuResolver):
    def __init__(self, table=None,branchId=None, branchMethod=None,webpage=None,
                        branchIdentifier=None, cacheTime=None,labelTemplate=None,
                        titleTemplate=None,label=None,title=None,**kwargs):
        super().__init__(table=table,
                            branchId=branchId,
                            label=label,
                            title=title,
                            branchMethod=branchMethod,
                            labelTemplate=labelTemplate,
                            titleTemplate=titleTemplate,
                            cacheTime=cacheTime if cacheTime is not None else 5,
                            webpage=webpage,branchIdentifier=branchIdentifier,**kwargs)
        self.table = table
        self.label = label
        self.title = title or label
        self.webpage = webpage
        self.branchIdentifier = branchIdentifier
        self.query_kwargs = dictExtract(kwargs,'query_')
        self.th_kwargs = dictExtract(kwargs,'th_')
        self.branchId = branchId
        self.labelTemplate = labelTemplate
        self.titleTemplate = titleTemplate or self.title
        self.branchMethod = branchMethod 

    @property
    def tblobj(self):
        return self._page.db.table(self.table)

    
    def getMenuContentHandler(self):
        handler = None
        if self.branchId:
            handler = getattr(self.tblobj,f'menu_dynamicMenuContent_{self.branchId}',None)
        if not handler:
            handler = self.tblobj.menu_dynamicMenuContent
        return handler
    
    def getMenuLineHandler(self):
        handler = None
        if self.branchId:
            handler = getattr(self.tblobj,f'menu_dynamicMenuLine_{self.branchId}',None)
        if not handler:
            handler = self.tblobj.menu_dynamicMenuLine
        return handler
    
 
    @property
    def sourceBag(self):
        result = MenuStruct()
        if self.branchMethod:
            getattr(self.tblobj,self.branchMethod)(result,**self.kwargs)
            return result
        selection = self.getMenuContentHandler()(**objectExtract(self,'query_'))
        webpagekw = dictExtract(self.kwargs,'webpage_')
        for record in selection:
            linekw = self.getMenuLineHandler()(record,labelTemplate=self.labelTemplate,
                                                titleTemplate=self.titleTemplate)
            linekw.setdefault('pageName',self.branchIdentifier)
            if self.webpage:
                kw = dict(webpagekw)
                kw.update(linekw)
                result.webpage(label = kw.pop('label'),url_pkey=record['pkey'],
                                filepath=self.webpage,url_branchIdentifier=self.branchIdentifier,
                                **{f'url_{k}':v for k,v in kw.items()})
            else:
                linekw.update(objectExtract(self,'th_',slicePrefix=False))
                result.thpage(start_pkey=record['pkey'],table=self.table,branchPage=True,
                                url_branchIdentifier=self.branchIdentifier,**linekw)
        return result


class LookupBranchResolver(MenuResolver):
    def __init__(self, pkg=None,tables=None,branchIdentifier=None,label=None,title=None,**kwargs):
        super().__init__(pkg=pkg,tables=tables,
                            branchIdentifier=branchIdentifier,
                            label=label,title=title,**kwargs)
        self.pkg = pkg
        self.tables = tables
        self.label = label
        self.title = title or label
        self.branchIdentifier = branchIdentifier

    
    def lookup_tables(self,pkg=None):
        for tbl in self._page.db.model.package(pkg).tables.values():
            tblattr = tbl.attributes
            if tblattr.get('lookup') and self._page.db.application.allowedByPreference(**tblattr):
                yield tbl.fullname

    @property
    def valid_packages(self):
        for pkgId,pkg in self._page.application.packages.items():
            attr = pkg.attributes
            if attr.get('_syspackage'):
                continue
            lookup_tables = list(self.lookup_tables(pkgId))
            if lookup_tables:
                yield pkg
 
    @property
    def sourceBag(self):
        result = MenuStruct()
        if self.tables:
            for tbl in self.tables.split(','):
                result.lookupPage(start_table=tbl,pageName=self.branchIdentifier,
                            title=self.title,branchPage=True,
                            url_branchIdentifier=self.branchIdentifier)
        elif self.pkg=='*':
            for pkgobj in self.valid_packages:
                result.lookupBranch(pkgobj.attributes.get('name_long'),
                                    title=self.title,pkg=pkgobj.id)
        else:
            for tbl in self.lookup_tables(self.pkg):
                result.lookupPage(start_table=tbl,pageName=self.branchIdentifier,
                                    title=self.title,branchPage=True,
                                    url_branchIdentifier=self.branchIdentifier)
        return result

class PackageMenuResolver(MenuResolver):
    def __init__(self, pkg=None,branchMethod=None, **kwargs):
       super().__init__(pkg=pkg,
                            branchMethod=branchMethod,
                            **kwargs)
       self.pkg = pkg
       self.branchMethod = branchMethod

    @property
    def sourceBag(self):
        return self.pkgMenu(self.pkg,branchMethod=self.branchMethod,
                            **dictExtract(self.kwargs,'branch_'))


class DirectoryMenuResolver(MenuResolver):
    def __init__(self, dirpath=None, **kwargs):
       super().__init__(dirpath=dirpath,**kwargs)
       self.dirpath = dirpath
       self.xmlresolved = False

    @property
    def sourceBag(self):
        result = MenuStruct()
        if self.pkg:
            folderSN = self._page.site.storageNode(f'pkg:{self.pkg}/webpages',self.folder)
        else:
            folderSN = self._page.site.storageNode(f'site:webpages',self.folder)
        for sn in folderSN.children():
            if sn.isfile and sn.ext=='py':
                filepath = sn.path.replace('.py','').replace('webpages/','')
                result.webpage(sn.cleanbasename.replace('_',' ').title(),
                                filepath=f"/{filepath}")
            elif sn.isdir and sn.basename!='__pycache__':
                result.directoryBranch(sn.cleanbasename.replace('_',' ').title(),
                                        folder=sn.path.replace(f'{self.pkg}/webpages',''),pkg=self.pkg)
        return result
