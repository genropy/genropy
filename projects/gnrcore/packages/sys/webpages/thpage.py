# -*- coding: utf-8 -*-

# thpage.py
# Created by Francesco Porcari on 2011-05-05.
# Copyright (c) 2011 Softwell. All rights reserved.



class GnrCustomWebPage(object):
    py_requires='public:TableHandlerMain'
    auth_main='user'

    def pageAuthTags(self, method=None, **kwargs):
        if getattr(self, '_page_init_error', None):
            return ''
        return self.auth_main

    def windowTitle(self):
        if getattr(self, '_page_init_error', None):
            return 'Not existing table'
        pkg, tbl = self.maintable.split('.')
        if not self.db.package(pkg) or tbl not in self.db.package(pkg).tables:
            return 'Not existing table'
        return self.db.table(self.maintable).attributes.get('name_plural') or self.db.table(self.maintable).attributes.get('name_long')


    @classmethod
    def getMainPackage(cls,request_args=None,request_kwargs=None):
        if request_kwargs.get('th_from_package'):
            return request_kwargs['th_from_package']
        if request_args and len(request_args) >= 2:
            return request_args[0]
        return 'sys'

    def onIniting(self, request_args, request_kwargs):
        if len(request_args) < 2:
            raise ValueError('Missing table arguments in URL: %s' % '/'.join(request_args))
        pageResource = request_kwargs.get('th_pageResource')
        if len(request_args)==3:
            pkg,tbl,pkey = request_args
        else:
            pkg,tbl = request_args

        defaultModule = 'th_%s' %tbl
        resourcePath = self._th_getResourceName(pageResource,defaultModule,'Page')
        self.mixinComponent(resourcePath,safeMode=True,only_callables=False)
        self.mixinComponent('tables',tbl,resourcePath,pkg=pkg,pkgOnly=True,safeMode=True,only_callables=False)
        self.mixinComponent('tables','_packages',pkg,tbl,resourcePath,pkg=self.packageId,pkgOnly=True,safeMode=True,only_callables=False)

    @property
    def maintable(self):
        callArgs = self.getCallArgs('th_pkg','th_table','th_pkey')
        return '%(th_pkg)s.%(th_table)s' %callArgs

    def deferredMainPageAuthTags(self,page):
        if hasattr(self,'root_tablehandler') and self.root_tablehandler.view.attributes.get('_notallowed'):
            return False
        if hasattr(self,'root_form') and self.root_form.attributes.get('_notallowed'):
            return False
        return True

    @property
    def pagename(self):
        callArgs = self.getCallArgs('th_pkg','th_table','th_pkey')
        return 'thpage_%(th_pkg)s_%(th_table)s' %callArgs

    def _showError(self, root, message):
        cp = root.contentPane(overflow='hidden',
            style='display:flex; align-items:center; justify-content:center; flex-direction:column; height:100%;')
        cp.img(src='/_rsrc/common/css_icons/svg/16/genrologo_sad.svg',
               height='64px', opacity='.5', margin_bottom='12px')
        cp.div(message,
               style='color:#888; font-size:13px; text-align:center; max-width:400px; line-height:1.5;')

    #FOR ALTERNATE MAIN HOOKS LOOK AT public:TableHandlerMain component
    def main(self,root,th_pkey=None,single_record=None,pkey=None,**kwargs):
        if getattr(self, '_page_init_error', None):
            self._showError(root, self._page_init_error)
            return
        pkg, tbl = self.maintable.split('.')
        if not self.db.package(pkg) or tbl not in self.db.package(pkg).tables:
            self._showError(root, "Table '%s' does not exist" % self.maintable)
            return
        tblattr = self.db.table(self.maintable).attributes
        if not self.application.allowedByPreference(**tblattr):
            raise self.exception('generic',description=f'Table {self.maintable} not allowed by preference')
        callArgs = self.getCallArgs('th_pkg','th_table','th_pkey')
        root.data('gnr.pagename', self.pagename)
        pkey = pkey or callArgs.pop('th_pkey',None)
        th_pkey = pkey or th_pkey
        if not single_record:
            root.rootTableHandler(th_pkey=th_pkey,**kwargs)
        else:
            self.main_form(root,single_record=single_record,th_pkey=th_pkey,**kwargs)
