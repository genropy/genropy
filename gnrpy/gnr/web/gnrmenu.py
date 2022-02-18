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
from attr import attr
from gnr.app.gnrconfig import MenuStruct
from gnr.core.gnrdict import dictExtract
from gnr.core.gnrbag import Bag,BagResolver,BagCbResolver,DirectoryResolver
from gnr.core.gnrlang import objectExtract


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
    def fullMenuBag(self):
        app = self._page.application
        if app.config['menu']:
            return app.config['menu']
        mainpackage = app.config['packages?main']
        if mainpackage:
            pkgMenus = [mainpackage]
        else:
            pkgMenus = app.config['menu?package']
            if pkgMenus:
                pkgMenus = pkgMenus.split(',')
            else:
                pkgMenus = list(app.packages.keys())
        
        if len(pkgMenus)==1:
            return app.packages[pkgMenus[0]].pkgMenu()
        else:
            result = MenuStruct()
            pkgMenuBag = None
            for pkgid in pkgMenus:
                apppkg = app.packages[pkgid]
                pkgMenuBag = apppkg.pkgMenu()
                if not pkgMenuBag:
                    continue
                pkgattrs = apppkg.attributes
                menu_label =pkgattrs.get('menu_label') or pkgattrs.get('name_long', pkgid)
                result.packageBranch(menu_label,pkg=pkgid)
            if len(result)==1:
                result = pkgMenuBag
        return result

    @property
    def sourceBag(self):
        if self.pkg:
            return self._page.application.packages[self.pkg].pkgMenu(branchMethod=self.branchMethod,**dictExtract(self.kwargs,'branch_'))
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
        value = self._page.application.packages[attributes['pkg']].pkgMenu(branchMethod=attributes.get('branchMethod'),
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
        pkgobj = self._page.application.packages[self.pkg]
        result = pkgobj.pkgMenu(branchMethod=self.branchMethod,**dictExtract(self.kwargs,'branch_'))
        return result


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