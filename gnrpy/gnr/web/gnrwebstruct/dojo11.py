#-*- coding: utf-8 -*-

#--------------------------------------------------------------------------
# package       : GenroPy web - see LICENSE for details
# module        : Genro Web structures - GnrDomSrc_dojo_11
# Copyright (c) : 2004 - 2007 Softwell sas - Milano
# Written by    : Giovanni Porcari, Michele Bertoldi
#                 Saverio Porcari, Francesco Porcari , Francesco Cavazzana
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

from gnr.core.gnrbag import Bag, BagCbResolver, DirectoryResolver
from gnr.core import gnrstring
from gnr.core.gnrdict import dictExtract

from gnr.web.gnrwebstruct.base import GnrDomSrc, GnrDomSrcError
from gnr.web.gnrwebstruct._helpers import _selected_defaultFrom
from gnr.web.widgets import AllWidgets


class GnrDomSrc_dojo_11(GnrDomSrc):
    """TODO"""

    # Widget namespace used by `__getattr__` to dispatch widget calls
    # through `child(tag)`. Populated from the declarative catalog in
    # `gnr.web.widgets`, where each dialect mixin (html, dijit, dojox,
    # genro) registers its widgets via the `@element` decorator. The
    # composed `AllWidgets` class resolves cross-dialect collisions
    # through its MRO (leftmost wins: Genro > Dojox > Dijit > Html).
    genroNameSpace = AllWidgets._widget_names
        
    #def framePane(self,slots=None,**kwargs):
    #    self.child('FramePane',slots='top,left,bottom,right',**kwargs)
        
    def dataFormula(self, path, formula, **kwargs):
        """Create a :ref:`dataformula` and returns it. dataFormula allows to calculate
        a value through a formula.
        
        :param path: the dataFormula's path
        :param formula: the dataFormula's formula
        :param **kwargs: formula parameters and other ones (:ref:`css`, etc)
        """
        return self.child('dataFormula', path=path, formula=formula, **kwargs)
        
    def dataScript(self, path, script, **kwargs):
        """.. warning:: deprecated since version 0.7. It has been substituted
                        by :ref:`datacontroller` and :ref:`dataformula`
        """
        return self.child('dataScript', path=path, script=script, **kwargs)
        
    def dataController(self, script=None, **kwargs):
        """Create a :ref:`datacontroller` and returns it. dataController allows to
        execute Javascript code
        
        :param script: the Javascript code that ``datacontroller`` has to execute. 
        :param **kwargs: *_init*, *_onStart*, *_timing*. For more information,
                      check the controllers' :ref:`controllers_attributes` section
        """
        return self.child('dataController', script=script, **kwargs)
        
    def dataRpc(self, pathOrMethod, method=None, **kwargs):
        """Create a :ref:`datarpc` and returns it. dataRpc allows the client to make a call
        to the server to perform an action and returns it.
        
        :param path: MANDATORY - it contains the folder path of the result of the ``dataRpc`` action;
                     you have to write it even if you don't return any value in the ``dataRpc``
                     (in this situation it will become a "mandatory but dummy" parameter)
        :param method: the name of your ``dataRpc`` method
        :param **kwargs: *_onCalling*, *_onResult*, *sync*. For more information,
                           check the :ref:`rpc_attributes` section
        """
        if not method and callable(pathOrMethod):
            method = pathOrMethod
            path = None
        else:
            path = pathOrMethod
        return self.child('dataRpc', path=path, method=method, **kwargs)
        
    def selectionstore_addcallback(self, *args, **kwargs):
        """TODO"""
        self.datarpc_addcallback(*args,**kwargs)
        
    def datarpc_addcallback(self, cb, **kwargs):
        """TODO
        
        :param cb: TODO
        :param **kwargs: TODO"""
        self.child('callBack',childcontent=cb,**kwargs)
        return self
        
    def datarpc_adderrback(self, cb, **kwargs):
        """TODO
        
        :param cb: TODO
        """
        self.child('callBack',childcontent=cb,_isErrBack=True,**kwargs)
        return self
        
    def slotButton(self, label=None, **kwargs):
        """Return a :ref:`slotbutton`. A slotbutton is a :ref:`button` with some preset attributes
        to create rapidly a button with an icon (set through the *iconClass* attribute) and with
        a label that works only as a tooltip: for example you can use a slotButton when you handle
        a :ref:`toolbar <toolbars>` or a :ref:`palette <palette>`
        
        :param label: the button's :ref:`tooltip` (or its label, if no *iconClass* is set)
        :param kwargs:
        
                       * **action**: allow to execute a javascript callback. For more information,
                         check the :ref:`action_attr` section
                       * **iconClass**: the button icon. For more information, check the :ref:`iconclass` section
                       * **showLabel**: boolean. If ``True``, show the button label
                       * **value**: specify the path of the widget's value. For more information,
                         check the :ref:`datapath` page
        """
        return self.child(tag='SlotButton',label=label,**kwargs)
        
    def virtualSelectionStore(self, table=None, storeCode=None, storepath=None, columns=None, **kwargs):
        """TODO
        
        :param table: the :ref:`database table <table>` name on which the query will be executed,
                      in the form ``packageName.tableName`` (packageName is the name of the
                      :ref:`package <packages>` to which the table belongs to)
        :param storeCode: TODO
        :param storepath: TODO
        :param columns: it represents the :ref:`columns` to be returned by the "SELECT"
                        clause in the traditional sql query. For more information, check the
                        :ref:`sql_columns` section
        """
        self.selectionStore(storeCode=storeCode,table=table, storepath=storepath,columns=columns,**kwargs)
        
    def _storeParentFrame(self):
        attr = self.attributes
        if attr.get('frameCode'):
            parentFramePaneNode = self.parentNode.attributeOwnerNode('tag',attrvalue='FramePane')
            parent = parentFramePaneNode.value 
        else:
            parent = self.parent
        return parent

    def selectionStore(self,table=None,storeCode=None,storepath=None,columns=None,handler=None,**kwargs):
        """TODO
        
        :param table: the :ref:`database table <table>` name on which the query will be executed,
                      in the form ``packageName.tableName`` (packageName is the name of the
                      :ref:`package <packages>` to which the table belongs to)
        :param storeCode: TODO
        :param storepath: TODO
        :param columns: it represents the :ref:`columns` to be returned by the "SELECT"
                        clause in the traditional sql query. For more information, check the
                        :ref:`sql_columns` section
        """
        attr = self.attributes
        parentTag = attr.get('tag')
        #columns = columns or '==gnr.getGridColumns(this);'
        parent = self
        if parentTag:
            parentTag = parentTag.lower()
        #storepath = storepath or attr.get('storepath') or '.grid.store'
        if storeCode:
            storepath = storepath or 'gnr.stores.%s.data' %storeCode            
        
        if parentTag =='includedview' or  parentTag =='newincludedview':
            attr['table'] = table
            storepath = storepath or attr.get('storepath') or '.store'
            storeCode = storeCode or attr.get('nodeId') or  attr.get('frameCode') 
            attr['store'] = storeCode
            parent = self._storeParentFrame()
        if parentTag == 'palettegrid':            
            storeCode=storeCode or attr.get('paletteCode')
            attr['store'] = storeCode
            attr['table'] = table
            storepath = storepath or attr.get('storepath') or '.store'
        nodeId = '%s_store' %storeCode
        return parent.child('SelectionStore',storepath=storepath, table=table, nodeId=nodeId,columns=columns,handler=handler,**kwargs)
        #ds = parent.dataSelection(storepath, table, nodeId=nodeId,columns=columns,**kwargs)
        #ds.addCallback('this.publish("loaded",{itemcount:result.attr.rowCount}')

    

    def bagStore(self,table=None,storeCode=None,storepath=None,columns=None,_identifier=None,**kwargs):
        """TODO
        
        :param table: the :ref:`database table <table>` name on which the query will be executed,
                      in the form ``packageName.tableName`` (packageName is the name of the
                      :ref:`package <packages>` to which the table belongs to)
        :param storeCode: TODO
        :param storepath: TODO
        :param columns: it represents the :ref:`columns` to be returned by the "SELECT"
                        clause in the traditional sql query. For more information, check the
                        :ref:`sql_columns` section
        """
        attr = self.attributes
        parentTag = attr.get('tag')
        #columns = columns or '==gnr.getGridColumns(this);'
        parent = self
        if parentTag:
            parentTag = parentTag.lower()
        #storepath = storepath or attr.get('storepath') or '.grid.store'

        if parentTag =='includedview' or  parentTag =='newincludedview':
            attr['table'] = attr.get('table') or table
            storepath = storepath or attr.get('storepath') or '.store'
            storeCode = storeCode or attr.get('nodeId') or  attr.get('frameCode') 
            attr['store'] = storeCode
            attr['tag'] = 'newincludedview'
            if _identifier:
                attr['identifier'] = _identifier
            parent = self._storeParentFrame()

        if parentTag == 'palettegrid':            
            storeCode=storeCode or attr.get('paletteCode')
            attr['store'] = storeCode
            attr['table'] = table
            if _identifier:
                attr['identifier'] = _identifier
            storepath = storepath or attr.get('storepath') or '.store'
        nodeId = '%s_store' %storeCode
        #self.data(storepath,Bag())
        return parent.child('BagStore',storepath=storepath, nodeId=nodeId,_identifier=_identifier,**kwargs)

    def fsStore(self,folders=None,storepath=None,storeCode=None,include='*.xml',columns=None,**kwargs):
        """FileSystem Store
        """
        attr = self.attributes
        parentTag = attr.get('tag')
        parent = self
        if parentTag:
            parentTag = parentTag.lower()
        if parentTag =='includedview' or  parentTag =='newincludedview':
            storepath = storepath or attr.get('storepath') or '.store'
            storeCode = storeCode or attr.get('nodeId') or  attr.get('frameCode') 
            attr['store'] = storeCode
            attr['tag'] = 'newincludedview'
            parent = self._storeParentFrame()
        if parentTag == 'palettegrid':            
            storeCode=storeCode or attr.get('paletteCode')
            attr['store'] = storeCode
            storepath = storepath or attr.get('storepath') or '.store'
        nodeId = '%s_store' %storeCode
        return parent.child('SelectionStore',storepath=storepath,storeType='FileSystem',
                            nodeId=nodeId,method='app.getFileSystemSelection',
                            folders=folders,include=include,columns=columns,
                            **kwargs)

    def rpcStore(self,rpcmethod=None,storepath=None,storeCode=None,columns=None,**kwargs):
        """RpcBase Store
        """
        attr = self.attributes
        parentTag = attr.get('tag')
        parent = self
        if parentTag:
            parentTag = parentTag.lower()
        if parentTag =='includedview' or  parentTag =='newincludedview':
            storepath = storepath or attr.get('storepath') or '.store'
            storeCode = storeCode or attr.get('nodeId') or  attr.get('frameCode') 
            attr['store'] = storeCode
            attr['tag'] = 'newincludedview'
            parent = self._storeParentFrame()
        if parentTag == 'palettegrid':            
            storeCode=storeCode or attr.get('paletteCode')
            attr['store'] = storeCode
            storepath = storepath or attr.get('storepath') or '.store'
        nodeId = '%s_store' %storeCode
        return parent.child('SelectionStore',storepath=storepath,storeType='RpcBase',
                            nodeId=nodeId,method=rpcmethod,**kwargs)

    def sharedObject(self,shared_path,shared_id=None,autoSave=None,autoLoad=None,**kwargs):
        return self.child(tag='SharedObject',shared_path=shared_path,shared_id=shared_id,autoSave=autoSave,autoLoad=autoLoad,**kwargs)
        
    def partitionController(self,partition_key=None,value=None,**kwargs):
        self.dataController(f"""
            let kw = {{}};
            kw.topic  = 'changed_partition_{partition_key}';
            kw.iframe = '*';
            genro.publish(kw,{{partition_value:value}});
        """,value=value,**kwargs)
        self.partitionSubscriber(partition_key)
    
    def partitionSubscriber(self,partition_key):
        self.data(f'current.{partition_key}',self.page.rootenv[f'current_{partition_key}'],serverpath=f'rootenv.current_{partition_key}',dbenv=True)
        self.dataFormula(f'current.{partition_key}','partition_value',
                         **{f'subscribe_changed_partition_{partition_key}':True})


    def onDbChanges(self, action=None, table=None, **kwargs):
        """TODO
        
        :param action: the :ref:`action_attr` attribute
        :param table: the :ref:`database table <table>`"""
        self.page.subscribeTable(table,True)
        self.dataController("""var _isLocalPageId = genro.isLocalPageId(_node.attr.from_page_id); 
                               %s""" % action,
                               dbChanges="^gnr.dbchanges.%s" %table.replace('.','_'),
                             **kwargs)


    def dataSelection(self, path, table=None, method='app.getSelection', columns=None, distinct=None,
                      where=None, order_by=None, group_by=None, having=None, columnsFromView=None, **kwargs):
        """Create a :ref:`dataselection` and returns it. dataSelection allows... TODO
        
        :param path: TODO
        :param table: the :ref:`database table <table>` name on which the query will be executed,
                      in the form ``packageName.tableName`` (packageName is the name of the
                      :ref:`package <packages>` to which the table belongs to)
        :param method: TODO
        :param columns: it represents the :ref:`columns` to be returned by the "SELECT"
                        clause in the traditional sql query. For more information, check the
                        :ref:`sql_columns` section
        :param distinct: boolean, ``True`` for getting a "SELECT DISTINCT"
        :param where: the sql "WHERE" clause. For more information check the :ref:`sql_where` section.
        :param order_by: corresponding to the sql "ORDER BY" operator. For more information check the
                         :ref:`sql_order_by` section
        :param group_by: the sql "GROUP BY" clause. For more information check the
                         :ref:`sql_group_by` section
        :param having: the sql "HAVING" clause. For more information check the :ref:`sql_having`
        :param columnsFromView: TODO
        :param **kwargs: *_onCalling*, *_onResult*, *sync*. For more information,
                           check the :ref:`rpc_attributes` section
        """
        if 'name' in kwargs:
            kwargs['_name'] = kwargs.pop('name')
        if 'content' in kwargs:
            kwargs['_content'] = kwargs.pop('content')
        if not columns:
            if columnsFromView:
                raise DeprecationWarning('columnsFromView is deprecated')
                columns = '=grids.%s.columns' % columnsFromView #it is the view id
            else:
                columns = '*'
                
        return self.child('dataRpc', path=path, table=table, method=method, columns=columns,
                          distinct=distinct, where=where, order_by=order_by, group_by=group_by,
                          having=having, **kwargs)
                          
    def directoryStore(self, rootpath=None, storepath='.store', **kwargs):
        """TODO
        
        :param rootpath: TODO
        :param storepath: TODO
        """
        store = DirectoryResolver(rootpath or '/', **kwargs)()
        self.data(storepath, store)
        
    def tableAnalyzeStore(self, table=None, where=None, group_by=None, storepath='.store.root',caption='Store',**kwargs):
        """TODO
        
        :param table: the :ref:`database table <table>` name on which the query will be executed,
                      in the form ``packageName.tableName`` (packageName is the name of the
                      :ref:`package <packages>` to which the table belongs to)
        :param where: the sql "WHERE" clause. For more information check the :ref:`sql_where`
                      section
        :param group_by: the sql "GROUP BY" clause. For more information check the
                         :ref:`sql_group_by` section
        :param storepath: TODO
        """
        self.data('.store',Bag(),caption=caption)
        self.dataRpc(storepath,'app.tableAnalyzeStore',table=table,where=where,group_by=group_by,**kwargs)
        
    def dataRecord(self, path, table, pkey=None, method='app.getRecord', **kwargs):
        """Create a :ref:`datarecord` and returns it. dataRecord allows... TODO
        
        :param path: TODO
        :param table: the :ref:`database table <table>` name on which the query will be executed,
                      in the form ``packageName.tableName`` (packageName is the name of the
                      :ref:`package <packages>` to which the table belongs to)
        :param pkey: the record :ref:`primary key <pkey>`
        :param method: TODO
        :param **kwargs: *_onCalling*, *_onResult*, *sync*. For more information,
                           check the :ref:`rpc_attributes` section
        """
        return self.child('dataRpc', path=path, table=table, pkey=pkey, method=method, **kwargs)
        
    def dataRemote(self, path, method,_resolved=None, **kwargs):
        """Create a :ref:`dataremote` and returns it. dataRemote is a synchronous :ref:`datarpc`:
        it calls a (specified) dataRspc as its resolver. When ``dataRemote`` is brought to the
        client, it will be changed in a Javascript resolver that at the desired path perform
        the rpc (indicated with the ``remote`` attribute).
        
        :param path: the path where the dataRemote will save the result of the rpc
        :param method: the rpc name that has to be executed
        :param **kwargs: *cacheTime=NUMBER*: The cache stores the retrieved value and keeps
                           it for a number of seconds equal to ``NUMBER``
        """
        childcontent =None
        if _resolved:
            resolved_kwargs = dictExtract(kwargs,'_resolved_',pop=True)
            kw = dict(kwargs)
            kw.update(resolved_kwargs)
            childcontent = method(**kw)
        return self.child('dataRemote', path=path, method=method,childcontent=childcontent,_resolved=_resolved, **kwargs)
        
    def dataResource(self, path, resource=None, ext=None, pkg=None):
        """Create a :ref:`dataresource` and returns it. dataResource is a :ref:`dataRemote`
        that allows... TODO
        
        :param path: TODO
        :param resource: TODO
        :param ext: TODO
        :param pkg: the :ref:`package <packages>` object
        """
        self.dataRemote(path,'getResourceContent',resource=resource,ext=ext, pkg=pkg)
        
    def paletteGroup(self, groupCode, **kwargs):
        """Return a :ref:`palettegroup`
        
        :param groupCode: TODO
        """
        return self.child('PaletteGroup',groupCode=groupCode,**kwargs)


    def docItem(self, store=None,key=None,contentpath=None,**kwargs):        
        return self.child('DocItem',store=store,key=key,contentpath=contentpath,**kwargs)

    def ckeditor(self,stylegroup=None,**kwargs):
        style_table = self.page.db.table('adm.ckstyle')
        if style_table:
            customStyles = style_table.getCustomStyles(stylegroup=stylegroup)
            if customStyles:
                kwargs['customStyles'] = customStyles
        return self.child('ckEditor',**kwargs)

    def palettePane(self, paletteCode, datapath=None, **kwargs):
        """Return a :ref:`palettepane`
        
        :param paletteCode: TODO. If no *datapath* is specified, the *paletteCode* will be used as *datapath*
        :param datapath: allow to create a hierarchy of your data’s addresses into the datastore.
                         For more information, check the :ref:`datapath` and the :ref:`datastore` pages
        """
        datapath= 'gnr.palettes.%s' %paletteCode if datapath is None else datapath
        return self.child('PalettePane',paletteCode=paletteCode,datapath=datapath,**kwargs)
        
    def paletteTree(self, paletteCode, datapath=None, **kwargs):
        """Return a :ref:`palettetree`
        
        :param paletteCode: TODO. If no *datapath* is specified, the *paletteCode* will be used as *datapath*
        :param datapath: allow to create a hierarchy of your data’s addresses into the datastore.
                         For more information, check the :ref:`datapath` and the :ref:`datastore` pages
        """
        datapath= datapath or 'gnr.palettes.%s' %paletteCode if datapath is None else datapath
        palette = self.child('PaletteTree',paletteCode=paletteCode,datapath=datapath,
                             autoslots='top,left,right,bottom',**kwargs)
        return palette
        
    def paletteGrid(self, paletteCode=None, struct=None,
                     columns=None, structpath=None, 
                     datapath=None,viewResource=None, **kwargs):
        """Return a :ref:`palettegrid`
        
        :param paletteCode: create the paletteGrid :ref:`nodeid` (if no *gridId* is defined)
                            and create the paletteGrid :ref:`datapath` (if no *datapath* is defined)
        :param struct: the name of the method that defines the :ref:`struct`
        :param columns: it represents the :ref:`columns` to be returned by the "SELECT"
                        clause in the traditional sql query. For more information, check the
                        :ref:`sql_columns` section
        :param structpath: TODO
        :param datapath: allow to create a hierarchy of your data’s addresses into the datastore.
                         For more information, check the :ref:`datapath` and the :ref:`datastore` pages
        :param kwargs: in the kwargs you find:
                       
                       * *dockButton*: boolean. if ``True``, TODO
                       * *grid_filteringGrid*: the path of the :ref:`grid` that handle the :ref:`struct`.
                         For example, in the :ref:`th` component the standard path for a grid is ``th.view.grid``
                       * *grid_filteringColumn*: allow the sincronization between the choosen columns and the
                         not choosen ones (so, if user drag a column in a grid, then this column doesn't appear
                         anymore in the palette)
                         
                         The syntax is::
                         
                            grid_filteringColumn='id:COLUMN'
                            
                         Where ``COLUMN`` is the name of a :ref:`column` TODO
                            
                       * *title*: the title of the paletteGrid
        """
        datapath= datapath or 'gnr.palettes.%s' %paletteCode if datapath is None else datapath
        structpath = structpath or '.grid.struct'
        kwargs['gridId'] = kwargs.get('gridId') or '%s_grid' %paletteCode
        paletteGrid = self.child('paletteGrid',paletteCode=paletteCode,
                                structpath=structpath,datapath=datapath,
                                viewResource=viewResource,
                                autoslots='top,left,right,bottom',**kwargs)
        if struct or columns or not structpath:
            paletteGrid.gridStruct(struct=struct,columns=columns)
        return paletteGrid
    
    def googlechart(self,chartType=None,**kwargs):
        return self.child('GoogleChart',chartType=chartType,**kwargs)
    
    def googlechart_column(self,field=None,name=None,dtype=None,**kwargs):
        columns = self.attributes.setdefault('columns',[])
        return columns.append(dict(field=field,name=name,dtype=dtype,**kwargs))

        
    def includedview_draganddrop(self,dropCodes=None,**kwargs):
        ivattr = self.attributes
        if dropCodes:
            for dropCode in dropCodes.split(','):
                mode = 'grid'
                if ':' in dropCode:
                    dropCode, mode = dropCode.split(':')
                dropmode = 'dropTarget_%s' % mode
                ivattr[dropmode] = '%s,%s' % (ivattr[dropmode], dropCode) if dropmode in ivattr else dropCode
                ivattr['onDrop_%s' % dropCode] = 'SET .droppedInfo_%s = dropInfo; FIRE .dropped_%s = data;' % (dropCode,dropCode)
                #ivattr['onCreated'] = """dojo.connect(widget,'_onFocus',function(){genro.publish("show_palette_%s")})""" % dropCode
                
    def newincludedview_footer(self,**kwargs):
        return self.child('footer',**kwargs)

    def footer_item(self,field=None,**kwargs):
        return self.child('item',field=field,**kwargs)

    def newincludedview_draganddrop(self,dropCodes=None,**kwargs):
        self.includedview_draganddrop(dropCodes=dropCodes,**kwargs)
        
    def includedview(self, *args, **kwargs):
        """The :ref:`includedview` component"""
        frameCode = kwargs.get('parentFrame') or self.attributes.get('frameCode')
        if frameCode and not kwargs.get('parentFrame')==False:
            kwargs['frameCode'] = frameCode
            return self.includedview_inframe(*args,**kwargs)
        else:
            return self.includedview_legacy(*args,**kwargs)
            
    def includedview_inframe(self, frameCode=None, struct=None, columns=None, storepath=None, structpath=None,
                             datapath=None, nodeId=None, configurable=None, _newGrid=False, childname=None, **kwargs):
        """TODO
        
        :param frameCode: TODO
        :param struct: the :ref:`struct` object
        :param columns: it represents the :ref:`columns` to be returned by the "SELECT"
                        clause in the traditional sql query. For more information, check the
                        :ref:`sql_columns` section
        :param storepath: TODO
        :param structpath: the :ref:`struct` path
        :param datapath: allow to create a hierarchy of your data’s addresses into the datastore.
                         For more information, check the :ref:`datapath` and the :ref:`datastore` pages
        :param nodeId: the page nodeId. For more information, check the :ref:`nodeid`
                       documentation page
        :param configurable: boolean. TODO
        :param _newGrid: boolean. TODO
        :param childname: the :ref:`childname`
        """
        nodeId = nodeId or '%s_grid' %frameCode
        if datapath is False:
            datapath = None
        elif storepath:
            datapath = datapath or '#FORM.%s' %nodeId 
        else:
            datapath = '.grid'
        structpath = structpath or '.struct'
        self.attributes['target'] = nodeId
        wdg = 'NewIncludedView' if _newGrid else 'includedView'
        relativeWorkspace = kwargs.pop('relativeWorkspace',True)
        childname=childname or 'grid'
        frameattributes = self.attributes
        if not self.attributes.get('frameCode'):
            frameattributes = self.root.getNodeByAttr('frameCode',frameCode).attr
        frameattributes['target'] = nodeId
        iv =self.child(wdg,frameCode=frameCode, datapath=datapath,structpath=structpath, nodeId=nodeId,
                     childname=childname,
                     relativeWorkspace=relativeWorkspace,configurable=configurable,
                     storepath=storepath,**kwargs)
        if struct or columns or not structpath:
            iv.gridStruct(struct=struct,columns=columns)
        return iv
        
    def includedview_legacy(self, storepath=None, structpath=None, struct=None, columns=None, table=None,
                            nodeId=None, relativeWorkspace=None, **kwargs):
        """TODO
        
        :param storepath: TODO
        :param structpath: the :ref:`struct` path
        :param struct: the :ref:`struct` object
        :param columns: it represents the :ref:`columns` to be returned by the "SELECT"
                        clause in the traditional sql query. For more information, check the
                        :ref:`sql_columns` section
        :param table: the :ref:`database table <table>` name on which the query will be executed,
                      in the form ``packageName.tableName`` (packageName is the name of the
                      :ref:`package <packages>` to which the table belongs to)
        :param nodeId: the :ref:`nodeid`
        :param relativeWorkspace: TODO
        """
        nodeId = nodeId or self.page.getUuid()
        prefix = 'grids.%s' %nodeId if not relativeWorkspace else ''
        structpath = structpath or '%s.struct' % prefix
        iv =self.child('includedView', storepath=storepath, structpath=structpath, nodeId=nodeId, table=table,
                          relativeWorkspace=relativeWorkspace,**kwargs)
        source = struct or columns
        if struct or columns or not structpath:
            iv.gridStruct(struct=struct,columns=columns)
        return iv
            
    def gridStruct(self, struct=None, columns=None):
        """TODO
        
        :param struct: the :ref:`struct` object
        :param columns: it represents the :ref:`columns` to be returned by the "SELECT"
                        clause in the traditional sql query. For more information, check the
                        :ref:`sql_columns` section
        """
        gridattr=self.attributes
        structpath = gridattr.get('structpath')
        table = gridattr.get('table')
        gridId= gridattr.get('nodeId') 
        storepath = gridattr.get('storepath')
        source = struct or columns
        page = self.page
        struct = page._prepareGridStruct(source=source,table=table,gridId=gridId)
        if struct:
            self.data(structpath, struct,childname='struct')
            return struct
        elif (source and not table) or not storepath:
            def getStruct(source=None,gridattr=None,gridId=None):
                storeCode = gridattr.get('store') or gridattr.get('nodeId') or gridattr.get('gridId')
                storeNode = page.pageSource('%s_store' %storeCode)
                table = gridattr.get('table')
                if storeNode:
                    table = storeNode.attr.get('table')
                    gridattr['table'] = table
                    #gridattr['storepath'] = '#%s_store.%s' %(storeCode,storeNode.attr.get('storepath'))
                return page._prepareGridStruct(source=source,table=table,gridId=gridId)
            struct = BagCbResolver(getStruct, source=source,gridattr=gridattr,gridId=gridId)
            struct._xmlEager=True
            self.data(structpath, struct)
        
    def slotToolbar(self,*args,**kwargs):
        """Create a :ref:`slotToolbar <slotbar>` and returns it
        
        .. note:: a slotToolbar is a :ref:`slotBar <slotbar>` with some css preset
        """
        kwargs.setdefault('toolbar', True)
        return self.slotBar(*args,**kwargs)
        
    def slotFooter(self,*args,**kwargs):
        """TODO"""
        kwargs['_class'] = 'frame_footer'
        return self.slotBar(*args,**kwargs)
        
    def _addSlot(self,slot,prefix=None,frame=None,frameCode=None,namespace=None,toolbarArgs=None):
        s=self.child('slot',childname=slot)
        s.frame = frame
        parameter = None
        slotCode = slot
        if '@' in slot:
            slotCode = slot.replace('@','_')
            slot,parameter = slot.split('@')
        slothandle = getattr(s,'%s_%s' %(prefix,slot),None)
        if not slothandle:
            if namespace:
                slothandle = getattr(s,'slotbar_%s_%s' %(namespace,slot),None)
            if not slothandle:
                slothandle = getattr(s,'slotbar_%s' %slot,None)
        if slothandle:
            kw = dict()
            kw[slot] = toolbarArgs.pop(slot,parameter)
            kw.update(dictExtract(toolbarArgs,'%s_' %slotCode,True))
            kw['frameCode'] = frameCode
            slothandle(**kw)
            
    def slotBar(self, slots=None, slotbarCode=None, namespace=None, childname='bar', **kwargs):
        """Create a :ref:`slotBar <slotbar>` and returns it. A slotBar is a Genro
        :ref:`toolbar <toolbars>`
        
        :param slots: MANDATORY. Create a configurable UI inside the div or :ref:`contentpane`
                      in which the slotToolbar is defined. For more information, check the
                      :ref:`slotbar_slots` section
        :param slotbarCode: autocreate a :ref:`nodeid` for the slotToolbar AND autocreate
                            hierarchic nodeIds for every slotToolbar child
        :param namespace: TODO
        :param childname: the slotBar :ref:`childname`
        """
        namespace = namespace or self.parent.attributes.get('namespace')
        tb = self.child('slotBar',slotbarCode=slotbarCode,slots=slots,childname=childname,**kwargs)
        toolbarArgs = tb.attributes
        slots = gnrstring.splitAndStrip(str(slots))
        frame = self.parent
        frameCode = self.getInheritedAttributes().get('frameCode')
        prefix = slotbarCode or frameCode
        for slot in slots:
            if slot!='*' and slot!='|' and not slot.isdigit():
                tb._addSlot(slot,prefix=prefix,frame=frame,frameCode=frameCode,namespace=namespace,toolbarArgs=toolbarArgs)
        return tb
        
        #se ritorni la toolbar hai una toolbar vuota 
    
    def slotbar_updateslotsattr(self,**kwargs):
        self.attributes.update(kwargs)
        toolbarArgs = self.attributes
        slotstr = toolbarArgs['slots']
        slots = gnrstring.splitAndStrip(slotstr)
        slotbarCode= toolbarArgs.get('slotbarCode')
        inattr = self.getInheritedAttributes()
        frameCode = inattr.get('frameCode')
        namespace = inattr.get('namespace')
        frame = self.parent.parent
        prefix = slotbarCode or frameCode
        for slot in slots:
            if slot!='*' and slot!='|' and not slot.isdigit():
                self.pop(slot)
                self._addSlot(slot,prefix=prefix,frame=frame,frameCode=frameCode,namespace=namespace,toolbarArgs=toolbarArgs)

    def slotbar_replaceslots(self, toReplace, replaceStr,**kwargs):
        """Allow to redefine the preset bars of the :ref:`slotBars <slotbar>` and the
        :ref:`slotToolbars <slotbar>`
        
        :param toReplace: MANDATORY. A string with the list of the slots to be replaced.
                          Use ``#`` to replace all the slots
        :param replaceStr: MANDATORY. A string with the list of the slots to add
        """
        self.attributes.update(kwargs)
        toolbarArgs = self.attributes
        slotstr = toolbarArgs['slots']
        slotbarCode= toolbarArgs.get('slotbarCode')
        if toReplace=='#':
            toReplace = slotstr
        replaceStr = replaceStr.replace('#',slotstr)
        slotstr = slotstr.replace(toReplace,replaceStr)
        toolbarArgs['slots'] = slotstr
        slots = gnrstring.splitAndStrip(slotstr)
        inattr = self.getInheritedAttributes()
        frameCode = inattr.get('frameCode')
        namespace = inattr.get('namespace')
        frame = self.parent.parent
        prefix = slotbarCode or frameCode
        for slot in slots:
            if slot!='*' and slot!='|' and not slot.isdigit():
                if not self.getNode(slot):
                    self._addSlot(slot,prefix=prefix,frame=frame,frameCode=frameCode,namespace=namespace,toolbarArgs=toolbarArgs)
        return self
                    
    def button(self, label=None, **kwargs):
        """The :ref:`button` is a :ref:`dojo-improved form widget <dojo_improved_widgets>`: through
        the *action* attribute you can add Javascript callbacks
        
        :param label: the label of the widget
        :param kwargs:
        
                       * **action**: allow to execute a javascript callback. For more information,
                         check the :ref:`action_attr` section
                       * **iconClass**: the button icon. For more information, check the :ref:`iconclass` section
                       * **showLabel**: boolean. If ``True``, show the button label
        """
        return self.child('button', label=label, **kwargs)
        
    def togglebutton(self, label=None, **kwargs):
        """A toggle button is a button that represents a setting with two states:
        ``True`` and ``False``. Use the *iconclass* attribute to allow the user
        to know (see) the current status
        
        :param label: the button's label
        :param kwargs: 
        
                       * **iconClass**: the button icon. For more information, check the :ref:`iconclass` section
                       * **showLabel**: boolean. If ``True``, show the button label
        """
        return self.child('togglebutton', label=label, **kwargs)
        
    def radiobutton(self, label=None, **kwargs):
        """:ref:`Radiobuttons <radiobutton>` are used when you want to let the user select
        one - and just one - option from a set of choices (if more options are to be allowed
        at the same time you should use :ref:`checkboxes <checkbox>` instead)
        
        :param label: the radiobutton label
        :param kwargs: 
                       
                       * *group*: allow to create a radiobutton group. To create a group, give
                         the same string to the *group* attribute of many radiobuttons. You can
                         obviously create more than a group giving a different string to the *group*
                         attribute (for more information, check the :ref:`rb_examples_group`)
        """
        return self.child('radiobutton', label=label, **kwargs)
        
    def checkbox(self, value=None, label=None,lbl=None,**kwargs):
        """Return a :ref:`checkbox`: setting the value to true will check the box
        while false will uncheck it

        :param label: the checkbox label
        :param value: the checkbox path for value. For more information, check the
                      :ref:`datapath` section
        """
        if lbl and not label and not getattr(self,'fbuilder',None):
            label = lbl
            lbl = '&nbsp;'
            # Auto-add formlet_fakelabel class to hide empty label row in formlet
            if 'box__class' not in kwargs:
                kwargs['box__class'] = 'formlet_fakelabel'
        return self.child('checkbox', value=value, label=label,lbl=lbl, **kwargs)
        
    def dropdownbutton(self, label=None, **kwargs):
        """The :ref:`dropdownbutton` can be used to build a :ref:`menu`
        
        :param label: the button label
        :param kwargs: 
                       
                       * **iconClass**: the button icon. For more information, check the :ref:`iconclass` section
                       * **showLabel**: boolean. If ``True``, show the button label
        """
        return self.child('dropdownbutton', label=label, **kwargs)
        
    def menuline(self, label=None, **kwargs):
        """A line of a :ref:`menu`
        
        :param label: the menuline label. Set it to "``-``" to create a dividing line
                      in the menu: ``menuline('-')``
        :param kwargs:
                       
                       * *action*: allow to execute a javascript callback. For more information, check
                         the :ref:`action_attr` page
                       * *checked*: boolean (by default is ``False``). If ``True``, allow to set a "V"
                         mark on the left side of the *menuline*
        """
        return self.child('menuline', label=label, **kwargs)

    def field(self, field=None, **kwargs):
        """``field`` is used to view, select and modify data included in a database :ref:`table`.

        Its type is inherited from :ref:`the type of data <datatype>` contained in the table to which
        ``field`` refers. For example, if the ``field`` is related to a column with the dtype set
        to "L" (integer number), then the relative widget is a :ref:`numbertextbox`, if the related
        column has a dtype set to "D", then the relative widget is a :ref:`datetextbox`, and so on

        .. note:: ``field`` MUST be a child of the :ref:`formbuilder` form widget, and
                  ``formbuilder`` itself MUST have a :ref:`datapath` for inner relative path gears
        
        :param field: MANDATORY - the column name to which field refers to. For more information,
                      check the :ref:`field_attr_field` section
        :param kwargs:
        
                       * **lbl**: Set the label of the field. If you don't specify it, then
                         ``field`` will inherit it from the :ref:`name_long` attribute of the requested data
                       * **rowcaption**: the textual representation of a record in a user query.
                         For more information, check the :ref:`rowcaption` section
        """
        newkwargs = self.prepareFieldAttributes(field, **kwargs)
        kwargs.pop('lbl',None)
        newkwargs.update(kwargs)
        tag = newkwargs.pop('tag')
        handler = getattr(self,tag)
        return handler(**newkwargs)
        
    def placeFields(self, fieldlist=None, **kwargs):
        """TODO"""
        for field in fieldlist.split(','):
            kwargs = self.prepareFieldAttributes(field)
            tag = kwargs.pop('tag')
            self.child(tag, **kwargs)
        return self
        
    def radiogroup(self, labels, group, cols=1, datapath=None, **kwargs):
        """.. warning:: deprecated since version 0.7"""
        if isinstance(labels, str):
            labels = labels.split(',')
        pane = self.div(datapath=datapath, **kwargs).formbuilder(cols=cols)
        for label in labels:
            if(datapath):
                pane.radioButton(label, group=group, datapath=':%s' % label)
            else:
                pane.radioButton(label, group=group)

    def prepareFieldAttributes(self, fld, **kwargs):
        parentfb = self.parentfb
        tblobj = None
        if '.' in fld and not fld.startswith('@'):
            x = fld.split('.', 2)
            maintable = '%s.%s' % (x[0], x[1])
            tblobj = self.page.db.table(maintable)
            fld = x[2]
        elif parentfb:
            assert hasattr(parentfb,'tblobj'),'missing default table. HINT: are you using a formStore in a bad place?'
            tblobj = parentfb.tblobj
        else:
            tbl = self.getInheritedAttributes().get('table')
            if not tbl:
                raise GnrDomSrcError('No table')
            else:
                tblobj = self.page.db.table(tbl)
        fieldobj = tblobj.column(fld)
        if fieldobj is None:
            raise GnrDomSrcError('Not existing field %s' % fld)
        wdgattr = self.wdgAttributesFromColumn(fieldobj, fld=fld,**kwargs)    
        wdgattr['helpcode'] =  fieldobj.fullname.replace('.','_')
        if fieldobj.attributes.get('_owner_package'):
            wdgattr['helpcode_package'] = fieldobj.attributes.get('_owner_package')
        if fieldobj.getTag() == 'virtual_column' or (('@' in fld ) and fld != tblobj.fullRelationPath(fld)):
            wdgattr.setdefault('readOnly', True)
            wdgattr['_virtual_column'] = fld
           
        if wdgattr['tag']in ('div', 'span'):
            wdgattr['innerHTML'] = '^.%s' % fld
        elif wdgattr['tag'] == 'tree':
            wdgattr['storepath'] = '.%s' % fld
            wdgattr['_fired'] ='^.%s' % fld
        else:
            wdgattr['value'] = '^.%s' % fld
        permissions = fieldobj.getPermissions(**self.page.permissionPars)
        if permissions.get('user_readonly'):
            wdgattr['readOnly'] = True
        if permissions.get('user_forbidden'):
            wdgattr['tag'] = 'div'
            wdgattr['_class'] = 'gnr_forbidden_field'
            wdgattr.pop('value',None)
            wdgattr.pop('innerHTML','&nbsp;')
        if permissions.get('user_blurred'):
            wdgattr['tag'] = 'div'
            wdgattr['_class'] = 'gnr_blurred_field'
        return wdgattr
        
    def wdgAttributesFromColumn(self, fieldobj,fld=None, **kwargs):
        """TODO
        
        :param fieldobj: TODO
        """
        lbl = kwargs.pop('lbl',None) 
        lbl =  fieldobj.name_long if lbl is None else lbl
        result = {'lbl': lbl,'field_name_long':fieldobj.name_long, 'dbfield': fieldobj.fullname}
        dtype = result['dtype'] = fieldobj.dtype
        fldattr =  dict(fieldobj.attributes or dict())
        result['format'] = fldattr.pop('format',None)
        col_size = fldattr.get('size')
        if dtype in ('A', 'C'):
            size = col_size
            if not size:
                size = '20'
            if ':' in size:
                size = size.split(':')[1]
            size = int(size)
        else:
            size = 5
        if fldattr.get('checkpref'):
            result['checkpref'] = fldattr['checkpref']
            result.update(dictExtract(fldattr,'checkpref_',slice_prefix=False))
        result.update(dictExtract(fldattr,'validate_',slice_prefix=False))
        result.update(dictExtract(fldattr,'wdg_'))
        if 'unmodifiable' in fldattr:
            result['unmodifiable'] = fldattr['unmodifiable']
        if 'protected' in fldattr:
            result['protected'] = fldattr['protected']
        relcol = fieldobj.relatedColumn()
        if relcol is not None:
            lnktblobj = relcol.table
            linktable_attr = lnktblobj.attributes
            if linktable_attr.get('checkpref'):
                result['checkpref'] = linktable_attr['checkpref']
                result.update(dictExtract(linktable_attr,'checkpref_'))
            isLookup = linktable_attr.get('lookup') or False
            joiner = fieldobj.relatedColumnJoiner()
            onerelfld = joiner['one_relation'].split('.')[2]
            if dtype in ('A', 'C'):
                size = lnktblobj.attributes.get('size', '20')
                if ':' in size:
                    size = size.split(':')[1]
                size = int(size)
            else:
                size = 5
            defaultZoom = self.getInheritedAttributes().get('enableZoom')
            if defaultZoom is None:
                defaultZoom = self.page.pageOptions.get('enableZoom', True)
            if lbl is not False:
                result['lbl'] = lbl or fieldobj.table.dbtable.relationName('@%s' % fieldobj.name)
                if kwargs.get('zoom', defaultZoom):
                    if hasattr(self.page,'_legacy'):
                        if hasattr(lnktblobj.dbtable, 'zoomUrl'):
                            zoomPage = lnktblobj.dbtable.zoomUrl()
                        else:
                            zoomPage = lnktblobj.fullname.replace('.', '/')
                        result['lbl_href'] = "=='/%s?pkey='+pkey" % zoomPage
                        result['lbl_pkey'] = '^.%s' %fld
                    else:
                        if hasattr(lnktblobj.dbtable, 'zoomUrl'):
                            pass
                        else:
                            zoomKw = dictExtract(kwargs,'zoom_')
                            forcedTitle = zoomKw.pop('title', None)
                            zoomKw.setdefault('formOnly',False)
                            result['lbl__zoomKw'] = zoomKw #,slice_prefix=False)
                            result['lbl__zoomKw_table'] = lnktblobj.fullname
                            result['lbl__zoomKw_lookup'] = isLookup
                            result['lbl__zoomKw_title'] = forcedTitle or lnktblobj.name_plural or lnktblobj.name_long
                            result['lbl__zoomKw_pkey'] = '=.%s' %fld
                            result['lbl_connect_onclick'] = "genro.dlg.zoomPaletteFromSourceNode(this,$1);"  
                    result['lbl'] = '<div class="gnrzoomicon">&nbsp;</div><div>%s</div>' %self.page._(result['lbl'])
                    result['lbl_class'] = 'gnrzoomlabel'
            result['tag'] = 'DbSelect'
            _selected_defaultFrom(fieldobj=fieldobj,result=result)
            result['dbtable'] = lnktblobj.fullname
            if '_storename' in joiner:
                result['_storename'] = joiner['_storename']
            elif 'storefield' in joiner:
                result['_storename'] = False if joiner['storefield'] is False else '=.%(storefield)s' %joiner
            #result['columns']=lnktblobj.rowcaption
            result['_class'] = 'linkerselect'
            result['searchDelay'] = 300
            result['ignoreCase'] = True
            result['method'] = 'app.dbSelect'
            result['size'] = size
            result['_guess_width'] = '%iem' % (int(size * .7) + 2)
            result.setdefault('hasDownArrow',isLookup)
            if(onerelfld != relcol.table.pkey):
                result['alternatePkey'] = onerelfld
        #elif attr.get('mode')=='M':
        #    result['tag']='bagfilteringtable'
        elif dtype in ('A', 'T') and fldattr.get('values', False):
            values = fldattr['values']
            values = getattr(fieldobj.table.dbtable, values ,lambda: values)()
            fldattr['values'] = values
            result['tag'] = 'filteringselect' if ':' in values else 'combobox'
            result['values'] = values
        elif dtype in ('A','T') and fldattr.get('dest_stn'):
            result['tag'] = 'modalUploader'
            result['dest_fld'] = fieldobj.fullname
            result.setdefault('enable','^#FORM.controller.is_newrecord?!=#v')
            result.setdefault('height','210px')
            result.setdefault('width','190px')
            result.setdefault('border','1px solid silver')
            result.setdefault('rounded',8)
            result.setdefault('dest_record_pkey','=#FORM.pkey')
            result.setdefault('label',result.pop('lbl',None))
            result.setdefault('extensions',fldattr.get('extensions',None))
        elif dtype == 'A':
            result['maxLength'] = size
            result['tag'] = 'textBox'
            result['_type'] = 'text'
            result['_guess_width'] = '%iem' % (int(size * .7) + 2)
        elif dtype == 'B':
            result['tag'] = 'checkBox'
            result.setdefault('html_label',not kwargs.get('label'))
            if 'autospan' in kwargs:
                kwargs['colspan'] = kwargs['autospan']
                del kwargs['autospan']
        elif dtype == 'T':
            result['tag'] = 'textBox'
            if col_size:
                result.setdefault('validate_len',col_size)
            result['_guess_width'] = '%iem' % int(size * .5)
        elif dtype == 'R':
            result['tag'] = 'numberTextBox'
            result['width'] = '7em'
        elif dtype == 'N':
            result['tag'] = 'numberTextBox'
            result['_guess_width'] = '7em'
        elif dtype == 'L' or dtype == 'I':
            result['tag'] = 'numberTextBox'
            result['places'] = 0
            result.setdefault('format','#,###')
            result['_guess_width'] = '7em'
        elif dtype == 'D':
            result['tag'] = 'dateTextBox'
            result['_guess_width'] = '9em'
        elif dtype == 'H':
            result['tag'] = 'timeTextBox'
            result['_guess_width'] = '7em'
        elif dtype == 'DH' or dtype=='DHZ':
            result['tag'] = result.get('tag') or 'dateTimeTextBox'
            result['_guess_width'] = '9em'
        elif dtype =='X':
            result['tag'] = 'tree'         
        else:
            result['tag'] = 'textBox'
        if kwargs:
            if kwargs.get('autospan', False):
                kwargs['colspan'] = kwargs.pop('autospan')
                kwargs['width'] = '99%'
            result.update(kwargs)
        if result['tag']=='textBox' and fldattr.get('localized'):
            result['tag'] = 'MultiLanguageTextBox'
            result['languages'] = fldattr.get('localized')
        return result
