#-*- coding: utf-8 -*-
#--------------------------------------------------------------------------
# package           : GenroPy web - see LICENSE for details
# module gnrwebcore : core module for genropy web framework
# Copyright (c)     : 2004 - 2019 Softwell sas - Milano 
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

import os
from gnr.core.gnrstructures import  GnrStructData
from gnr.core.gnrdict import dictExtract
from gnr.core.gnrbag import Bag,BagResolver,BagCbResolver,DirectoryResolver
from gnr.core.gnrlang import objectExtract
from gnr.core.gnrstring import slugify
from gnr.app.gnrconfig import ConfigStruct

class MenuStruct(ConfigStruct):
    
    def branch(self, label, basepath=None ,tags='',pkg=None,**kwargs):
        return self.child('branch',label=label,basepath=basepath,tags=tags,pkg=pkg,**kwargs)
    
    def webpage(self, label,filepath=None,tags='',multipage=None, **kwargs):
        return self.child('webpage',label=label,multipage=multipage,tags=tags,file=filepath,_returnStruct=False,**kwargs)

    def thpage(self, label,table=None,tags='',multipage=None, **kwargs):
        return self.child('thpage',label=label,table=table,
                            multipage=multipage,tags=tags,_returnStruct=False,**kwargs)

    def lookups(self,label,lookup_manager=None,tags=None,**kwargs):
        return self.child('lookups',label=label,lookup_manager=lookup_manager,tags=tags,_returnStruct=False,**kwargs)

            
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
            text = """#!/usr/bin/env python
# encoding: utf-8
def config(root,application=None):"""         
            f.write(text)
            self._toPythonInner(f,self,'root')


    def _toPythonInner(self,filehandle,b,rootname):
        filehandle.write('\n')
        for n in b:
            kw = dict(n.attr)
            label = kw.pop('label',n.label)
            attrlist = ['u"%s"' %label]
            for k,v in list(kw.items()):
                if k=='file':
                    k = 'filepath'
                attrlist.append('%s="%s"' %(k,v))
            if n.value:
                varname = slugify(label).replace('!!','').replace('-','_')
                filehandle.write('    %s = %s.branch(%s)' %(varname,rootname,', '.join(attrlist)))
                self._toPythonInner(filehandle,n.value,varname) 
            elif 'table' in kw:
                filehandle.write('    %s.thpage(%s)' %(rootname,', '.join(attrlist)))
            elif 'lookup_manager' in kw:
                filehandle.write('    %s.lookups(%s)' %(rootname,', '.join(attrlist)))
            elif 'pkg' in kw:
                filehandle.write('    %s.branch(%s)' %(rootname,', '.join(attrlist)))
            else:
                filehandle.write('    %s.webpage(%s)' %(rootname,', '.join(attrlist)))
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
        pkgMenu = MenuStruct(os.path.join(pkg.packageFolder, 'menu'),
                                config_method=branchMethod, 
                                application=self.app,autoconvert=True,
                                **kwargs)
        for pluginname,plugin in list(pkg.plugins.items()):
            pluginmenu = os.path.join(plugin.pluginFolder,'menu')
            if os.path.exists(pluginmenu):
                pkgMenu.update(MenuStruct(pluginmenu,application=self.app,autoconvert=True))
        return pkgMenu

    def getPkg(self,pkgId):
        return self.app.packages[pkgId]


    def getInstanceMenu(self):
        #legacy
        menuinstance = os.path.join(self.app.instanceFolder, 'menu')
        if os.path.exists(menuinstance):
            return MenuStruct(menuinstance,application=self.app,autoconvert=True)


    @property
    def fullMenuBag(self):
        instanceMenu = self.getInstanceMenu()
        if instanceMenu:
            return instanceMenu
        mainpackage = self.app.config['packages?main']
        if mainpackage:
            pkgMenus = [mainpackage]
        else:
            pkgMenus = self.app.config['menu?package']
            if pkgMenus:
                pkgMenus = pkgMenus.split(',')
            else:
                pkgMenus = list(self.app.packages.keys())
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
        return self.fullMenuBag


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
            externalSite = self.checkExternalSiteUrl(node)
            labelClass = f'menu_shape menu_level_{self.level}'
            customLabelClass = node.attr.get('customLabelClass')
            if customLabelClass:
                labelClass = f'{labelClass} {customLabelClass}'
            if attributes.get('workInProgress'):
                labelClass = f'{labelClass} workInProgress'
            attributes['labelClass'] = labelClass
            if externalSite:
                attributes['externalSite'] = externalSite
            result.setItem(node.label, value, attributes)
        return result

    def checkLegacyNode(self,node):
        nodeattr = node.attr
        nodeTag = nodeattr.get('tag')
        if nodeTag == 'branch':
            if nodeattr.get('pkg'):
                nodeattr['tag'] = 'packageBranch'
                return 'updateToPackageBranch'
            if nodeattr.get('dashboard'):
                nodeattr['tag'] = 'dashboardBranch'
                return 'updateToDashboardBranch'
            if nodeattr.get('dir'):
                nodeattr['tag'] = 'directoryBranch'
                return 'updateToDirectoryBranch'

        if nodeTag=='webpage' and nodeattr.get('table'):
            nodeattr['tag'] = 'thpage'
            return 'thpage'
        if nodeTag=='thpage' and nodeattr.get('file'):
            nodeattr['tag'] = 'webpage'

    def checkExternalSiteUrl(self,node):
        externalSite = node.attr.get('externalSite')
        if externalSite:
            return self._page.site.config['externalSites'].getAttr(externalSite)['url']

    @property
    def level(self):
        return self.level_offset+(len(self.path.split('.')) if self.path else 0)

    def allowedNode(self,node):
        nodeattr = node.attr
        auth_tags = nodeattr.get('tags')
        if auth_tags and \
            not self._page.application.checkResourcePermission(auth_tags, self._page.userTags):
            return False
        multidb = nodeattr.get('multidb')
        dbstore = self._page.dbstore
        if (multidb=='slave' and not dbstore) or (multidb=='master' and dbstore):
            return False
        checkenv = nodeattr.get('checkenv')
        if checkenv and not self._page.rootenv[checkenv]:
            return False
        if not self._page.application.allowedByPreference(**nodeattr):
            return False
        return True


    def _getDashboards(self,pkg=None):
        if not self._page.db.package('biz'):
            return
        result = Bag()
        f = self._page.db.table('biz.dashboard').query(where='$pkgid=:pk' if pkg is not True else None).fetch()
        for i,r in enumerate(f):
            if r['private']:
                continue
            label = 'dash_%s' %i
            result.setItem(label,None,file='/biz/dashboards/%(pkgid)s/%(code)s' %r,label=r['description'] or r['code'])
        return result

    def nodeType_lookups(self,node):
        attributes = dict(node.attr)
        return None,attributes

    def nodeType_webpage(self,node):
        attributes = dict(node.attr)
        if not self._page.checkPermission(attributes['file']):
            raise NotAllowedException('Not allowed page')
        return None,attributes

    def nodeType_thpage(self,node):
        attributes = dict(node.attr)
        aux_instance = attributes.get('aux_instance') or self.aux_instance
        attributes['aux_instance'] = aux_instance
        pkey = attributes.pop('pkey',None)
        if pkey:
            attributes.setdefault('subtab',True)
            attributes.setdefault('url_main_call','main_form')
            attributes['url_th_pkey'] = pkey
            attributes['url_linker'] = True
            attributes['multipage'] = False 

            #attributes.setdefault('url_th_public',True)
        if not aux_instance:
            table = attributes['table']
            tableattr = self._page.db.table(table).attributes
            if not self._page.application.allowedByPreference(**tableattr):
                raise NotAllowedException('Not allowed by preference')
        return None,attributes

    def nodeType_directoryBranch(self,node):
        attributes = dict(node.attr)
        return DirectoryMenuResolver(level_offset=self.level,
                                    
                                aux_instance=attributes.get('aux_instance') or self.aux_instance,
                                externalSite= attributes.get('externalSite') or self.externalSite,
                                _page=self._page),attributes

    def nodeType_tableBranch(self,node):
        kwargs = dict(node.attr)
        kwargs.pop('tag')
        cacheTime = kwargs.pop('cacheTime',None)
        xmlresolved = kwargs.pop('resolved',False)
        sbresolver = TableMenuResolver(xmlresolved=xmlresolved,
                            _page=self._page,cacheTime=cacheTime, 
                            **kwargs)
        attributes = dict(node.attr)
        attributes['isDir'] = True
        return sbresolver,attributes

    def nodeType_packageBranch(self,node):
        attributes = dict(node.attr)
        value = self.pkgMenu(attributes['pkg'],branchMethod=attributes.get('branchMethod'),
                                **dictExtract(attributes,'branch_'))
        path = None
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
    def __init__(self, table=None,branchVariant=None, branchMethod=None,webpage=None, **kwargs):
       super().__init__(table=table,
                            branchVariant=branchVariant,
                            branchMethod=branchMethod,
                            webpage=webpage,**kwargs)
       self.table = table
       self.webpage = webpage
       self.query_kwargs = dictExtract(kwargs,'query_')
       self.th_kwargs = dictExtract(kwargs,'th_')
       self.branchVariant = branchVariant
       self.branchMethod = branchMethod 

    @property
    def tblobj(self):
        return self._page.db.table(self.table)

    
    def getMenuContentHandler(self):
        handler = None
        if self.branchVariant:
            handler = getattr(self.tblobj,f'menu_dynamicMenuContent_{self.branchVariant}',None)
        if not handler:
            handler = self.tblobj.menu_dynamicMenuContent
        return handler
    
    def getMenuLineHandler(self):
        handler = None
        if self.branchVariant:
            handler = getattr(self.tblobj,f'menu_dynamicMenuLine_{self.branchVariant}',None)
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
            linekw = self.getMenuLineHandler()(record)
            if self.webpage:
                kw = dict(webpagekw)
                kw.update(linekw)
                result.webpage(label = kw.pop('label'),url_pkey=record['pkey'],filepath=self.webpage,**{f'url_{k}':v for k,v in kw.items()})
            else:
                linekw.update(objectExtract(self,'th_',slicePrefix=False))
                result.thpage(pkey=record['pkey'],table=self.table,**linekw)
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
        return self.pkgMenu(self.pkg,branchMethod=self.branchMethod,**dictExtract(self.kwargs,'branch_'))


class DirectoryMenuResolver(MenuResolver):
    def __init__(self, dirpath=None, **kwargs):
       super().__init__(dirpath=dirpath,**kwargs)
       self.dirpath = dirpath

    @property
    def sourceBag(self):
        result = MenuStruct()
        for sn in self._page.site.storageNode(self.dirpath).children:
            if sn.isfile and sn.extension=='py':
                result.webpage(sn.cleanbasename.replace('_',' ').title(),
                                file=sn.url)
            elif sn.isdir:
                result.directoryBranch(sn.cleanbasename.replace('_',' ').title(),
                                        dir=sn.path)
        return result