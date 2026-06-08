#-*- coding: utf-8 -*-

#--------------------------------------------------------------------------
# package       : GenroPy web - see LICENSE for details
# module        : Genro Web structures - GnrDomSrc base
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

import os
from copy import copy

from gnr.core.gnrbag import Bag
from gnr.core.gnrstructures import GnrStructData
from gnr.core.gnrdict import dictExtract
from gnr.core.gnrdecorator import extract_kwargs, deprecated

from gnr.web.gnrwebstruct.formbuilder import GnrFormBuilder


class StructMethodError(Exception):
    pass


def struct_method(func_or_name):
    """A decorator. Allow to register a new method (in a page or in a component)
    that will be available in the web structs::

        @struct_method
        def includedViewBox(self, bc, ...):
            pass

        def somewhereElse(self, bc):
            bc.includedViewBox(...)

    If the method name includes an underscore, only the part that follows the first
    underscore will be the struct method's name::

        @struct_method
        def iv_foo(self, bc, ...):
            pass

        def somewhereElse(self, bc):
            bc.foo(...)

    You can also pass a name explicitly::

        @struct_method('bar')
        def foo(self, bc, ...):
            pass

        def somewhereElse(self, bc):
            bc.bar(...)"""
    def register(name, func):
        func_name = func.__name__
        existing_name = GnrDomSrc._external_methods.get(name, None)
        if existing_name and (existing_name != func_name):
            # If you want to override a struct_method, be sure to call its implementation method in the same way as the original.
            # (Otherwise, the result would NOT  be well defined due to uncertainty in the mixin process at runtime plus the fact that the GnrDomSrc is global)
            raise StructMethodError(
                    "struct_method %s is already tied to implementation method %s" % (repr(name), repr(existing_name)))
        GnrDomSrc._external_methods[name] = func_name

    if isinstance(func_or_name, str):
        name = func_or_name

        def decorate(func):
            register(name, func)
            return func

        return decorate
    else:
        name = func_or_name.__name__
        if '_' in name:
            name = name.split('_', 1)[1]
        register(name, func_or_name)
        return func_or_name


class GnrDomSrcError(Exception):
    pass


class GnrDomElem(object):
    def __init__(self, obj, tag):
        self.obj = obj
        self.tag = tag

    def __call__(self, *args, **kwargs):
        child = self.obj.child(self.tag, *args, **kwargs)
        return child


class GnrDomSrc(GnrStructData):
    """GnrDomSrc class"""
    _external_methods = dict()
    
    def js_sourceNode(self,mode=''):
        return "==pyref('%s','%s')" % (self.attributes.setdefault('__ref','%s_%i' % (self.parentNode.attr.get('tag',''),id(self.parentNode))),mode)

    @property
    def js_widget(self):
        """TODO"""
        return self.js_sourceNode('w')
    
    @property
    def js_domNode(self):
        """TODO"""
        return self.js_sourceNode('d')
        
    @property
    def js_form(self):
        """TODO"""
        return self.js_sourceNode('f')
    
    def makeRoot(cls, page, source=None,rootAttributes=None):
        """Build the root through the :meth:`makeRoot()
        <gnr.core.gnrstructures.GnrStructData.makeRoot>` method and return it
        
        :param cls: the structure class
        :param page: the webpage instance
        :param source: the filepath of the xml file"""
        root = GnrStructData.makeRoot(source=source, protocls=cls,rootAttributes=rootAttributes)
        root._page = page
        return root
    makeRoot = classmethod(makeRoot)


    def _get_page(self):
        return self.root._page
    page = property(_get_page)
    
    def checkNodeId(self, nodeId):
        """Check if the :ref:`nodeid` is already existing or not
        
        :param nodeId: the :ref:`nodeid`"""
        assert nodeId not in self.register_nodeId,'%s is duplicated' %nodeId
        self.page._register_nodeId[nodeId] = self
        
    @property
    def register_nodeId(self):
        """TODO"""
        if not hasattr(self.page,'_register_nodeId'):
            register = dict()
            self.page._register_nodeId = register
        return self.page._register_nodeId
        
    def _get_parentfb(self):
        if hasattr(self, 'fbuilder'):
            return self.fbuilder
        elif self.parent:
            return self.parent.parentfb
    parentfb = property(_get_parentfb)
            
    def __getattr__(self, fname):
        fnamelower = fname.lower()
        if (fname != fnamelower) and hasattr(self, fnamelower):
            return getattr(self, fnamelower)
        # Attached sub-nodes must win over the widget catalog: an explicit
        # named child is stateful (attributes, children), while the widget
        # entry would build a brand-new element and orphan the existing node.
        attachnode = self.getNode(fname)
        if attachnode:
            return attachnode._value
        if fnamelower in self.genroNameSpace:
            return GnrDomElem(self, '%s' % (self.genroNameSpace[fnamelower]))
        if fname in self._external_methods:
            method_name = self._external_methods[fname]
            handler = getattr(self.page, method_name, None)
            if handler is None:
                page_name = os.path.basename(getattr(self.page, 'filepath', '') or '')
                raise AttributeError(
                    "Struct method '%s' not found in page '%s'"
                    " — check py_requires" % (method_name, page_name))
            return lambda *args, **kwargs: handler(self, *args,**kwargs)
        autoslots = self._parentNode.attr.get('autoslots')
        if autoslots:
            autoslots = autoslots.split(',')
            if fname in autoslots:
                return self.child('autoslot',childname=fname)
        parentTag = self._parentNode.attr.get('tag','').lower()
        if parentTag and not fnamelower.startswith(parentTag):
            subtag = ('%s_%s' %(parentTag,fname)).lower()
            if hasattr(self,subtag):
                return getattr(self,subtag)
        page_name = os.path.basename(getattr(self.page, 'filepath', '') or '')
        raise AttributeError("'%s' is not defined in page '%s'"
                    " — check py_requires" % (fname, page_name))
    
    @deprecated
    def getAttach(self, childname):
        """.. warning:: deprecated since version 0.7"""
        childnode = self.getNode(childname)
        if childnode:
            return childnode._value
        
    def child(self, tag, childname=None, childcontent=None, envelope=None,_tablePermissions=None,**kwargs):
        """Set a new item of the ``tag`` type into the current structure through
        the :meth:`child() <gnr.core.gnrstructures.GnrStructData.child>` and return it
        
        :param tag: the html tag
        :param childname: the :ref:`childname`
        :param childcontent: the html content
        :param envelope: TODO"""
        if childname and childname.startswith('^') and 'value' not in kwargs:
            kwargs['value'] = childname
            childname = None
        if '_tags' in kwargs and not self.page.application.checkResourcePermission(kwargs['_tags'], self.page.userTags):
            kwargs['__forbidden__'] = True
        if _tablePermissions and _tablePermissions.get('table') \
            and not self.page.checkTablePermission(**_tablePermissions):
            kwargs['__forbidden__'] = True
        if not self.page.application.allowedByPreference(**kwargs):
            kwargs['__forbidden__'] = True
        if 'fld' in kwargs:
            fld_dict = self.getField(kwargs.pop('fld'))
            fld_dict.update(kwargs)
            kwargs = fld_dict
            t = kwargs.pop('tag', tag)
            if tag == 'input':
                tag = t
        if hasattr(self, 'fbuilder'):
            if tag not in (
            'tr', 'data', 'script', 'func', 'connect', 'dataFormula', 'dataScript', 'dataRpc', 'dataRemote',
            'dataRecord', 'dataSelection', 'dataController'):
                if tag == 'br':
                    return self.fbuilder.br()
                if 'disabled' not in kwargs:
                    if hasattr(self, 'childrenDisabled'):
                        kwargs['disabled'] = self.childrenDisabled
                return self.fbuilder.place(tag=tag, childname=childname, **kwargs)
        if envelope:
            obj = GnrStructData.child(self, 'div', childname='*_#', **envelope)
        else:
            obj = self
        for k,v in list(kwargs.items()):
            if isinstance(v,GnrStructData):
                kwargs[k]=v.js_sourceNode()
        if kwargs.get('nodeId'):
            self.checkNodeId(kwargs['nodeId'])
        sourceNodeValueAttr = dictExtract(kwargs,'attr_')
        serverpath = sourceNodeValueAttr.get('serverpath')
       # dbenv = sourceNodeValueAttr.get('dbenv')
        if serverpath: #or dbenv:
            clientpath = kwargs.get('value') or kwargs.get('src') or kwargs.get('innerHTML')
            if clientpath:
                clientpath = clientpath.replace('^','').replace('=','')
                value=kwargs.get('default_value')
                self.data(clientpath,value,**sourceNodeValueAttr)
        if childname and childname != '*_#':
            kwargs['_childname'] = childname
        _strippedKwargs=','.join([k for k,v in list(kwargs.items()) if v is None])
        if _strippedKwargs:
            kwargs['_strippedKwargs'] = _strippedKwargs
        return GnrStructData.child(obj, tag, childname=childname, childcontent=childcontent,**kwargs)
        
    def htmlChild(self, tag, childcontent, value=None, **kwargs):
        """Create an html child and return it
        
        :param tag: the html tag
        :param childcontent: the html content
        :param value: TODO"""
        if childcontent is not None :
            kwargs['innerHTML'] = childcontent
            childcontent = None
        elif value is not None:
            kwargs['innerHTML'] = value
            value = None
        return self.child(tag, childcontent=childcontent, **kwargs)
        
    def nodeById(self, id):
        """TODO
        
        :param id: the :ref:`nodeid`"""
        return self.findNodeByAttr('nodeId', id)
        
    def fullScreenDialog(self,backTitle='!!Back',**kwargs):
        dlg = self.dialog(fullScreen=True,**kwargs)
        frame = dlg.framePane(childname='center')
        bar = frame.top.slotBar('backTitle,*',_class='slotbar_toolbar_lg',font_weight='bold',
                             color='var(--mainWindow-color)',border_bottom='1px solid silver')
        btn = bar.backTitle.lightButton(action="_dlg.hide();",_dlg=dlg.js_widget,style='display:flex;align-items:center;',cursor='pointer')
        btn.div(_class="iconbox leftOut",height='25px',background_color='var(--mainWindow-color)')
        btn.div(backTitle)
        return dlg

    def framepane(self, frameCode=None, centerCb=None, **kwargs):
        """Create a :ref:`framepane` and return it. A framePane is a :ref:`bordercontainer`
        with :ref:`frame_sides` attribute added: these sides follow the Dojo borderContainer
        suddivision: there is indeed the *top*, *bottom*, *left*, *right* and *center* regions
        
        :param frameCode: the framepane code
        :param centerCb: TODO"""
        frameCode = frameCode or 'frame_#'
        if '#' in frameCode:
            frameCode = frameCode.replace('#',self.page.getUuid())
        frame = self.child('FramePane',frameCode=frameCode,autoslots='top,bottom,left,right,center',**kwargs)
        if callable(centerCb):
            centerCb(frame)
        return frame
        
    @property
    def record(self):
        tag = self.attributes.get('tag')
        if tag == 'FrameForm':
            return self.center.contentPane(datapath='.record')
        if tag == 'BoxForm':
            node = self.getNode('recordbox')
            if node:
                return node._value
            return self.child('div', childname='recordbox', datapath='.record')
        assert False, 'only on FrameForm or BoxForm'

    def chartpane(self,**kwargs):
        self.page.mixinComponent('js_plugins/chartjs/chartjs:ChartPane')
        self.child('chartpane',**kwargs)

    def palettechart(self,**kwargs):
        self.page.mixinComponent('js_plugins/chartjs/chartjs:ChartPane')
        self.child('palettechart',**kwargs)

    def statspane(self,**kwargs):
        self.page.mixinComponent('js_plugins/statspane/statspane:StatsPane')
        self.child('statspane',**kwargs)

    def palettestats(self,**kwargs):
        self.page.mixinComponent('js_plugins/statspane/statspane:StatsPane')
        self.child('palettestats',**kwargs)


    @extract_kwargs(store=True)
    def frameform(self, formId=None, frameCode=None, store=None,storeType=None, storeCode=None,
                  slots=None, table=None, store_kwargs=None, **kwargs):
        """TODO
        
        ``frameform()`` method is decorated with the :meth:`extract_kwargs <gnr.core.gnrdecorator.extract_kwargs>` decorator
        
        :param formId: TODO
        :param frameCode: TODO
        :param store: TODO
        :param storeCode: TODO
        :param slots: TODO
        :param table: the :ref:`database table <table>` name on which the query will be executed,
                      in the form ``packageName.tableName`` (packageName is the name of the
                      :ref:`package <packages>` to which the table belongs to)
        :param store_kwargs: TODO"""
        formId = formId or '%s_form' %frameCode
        if not storeCode:
            storeCode = formId
        if not table:
            storeNode = self.root.nodeById('%s_store' %storeCode)
            if storeNode:
                table = storeNode.attr['table']
        centerCb = kwargs.pop('centerCb',None)
        frame = self.child('FrameForm',formId=formId,frameCode=frameCode,
                            namespace='form',storeCode=storeCode,table=table,
                            autoslots='top,bottom,left,right,center',**kwargs)
        if store:
            store_kwargs['storeType'] = storeType or store_kwargs.get('storeType')
            if store is True:
                store = 'recordCluster'
            store_kwargs['handler'] = store
            frame.formStore(**store_kwargs)
        if callable(centerCb):
            centerCb(frame)
        return frame
        
    def formstore(self, handler='recordCluster', nodeId=None, table=None,
                  storeType=None, parentStore=None, **kwargs):
        """TODO
        
        :param storepath: TODO
        :param handler: TODO
        :param nodeId: the page nodeId. For more information, check the :ref:`nodeid`
                       documentation page
        :param table: the :ref:`database table <table>` name on which the query will be executed,
                      in the form ``packageName.tableName`` (packageName is the name of the
                      :ref:`package <packages>` to which the table belongs to)
        :param storeType: TODO
        :param parentStore: TODO"""
        assert self.attributes.get('tag','').lower()=='frameform', 'formstore can be created only inside a FrameForm'
        storeCode = self.attributes['frameCode']
        self.attributes['storeCode'] = storeCode
        if not storeType:
            if parentStore:
                storeType='Collection'
            else:
                storeType='Item'
        if table:
            self.attributes['table'] = table
        elif 'table' in self.attributes:
            table = self.attributes['table']
        if table:
            tblattr = dict(self.page.db.table(table).attributes)
            tblattr.pop('tag',None)
            self.data('.controller.table',table,**tblattr)
        return self.child('formStore',childname='store',storeCode=storeCode,table=table,
                            nodeId = nodeId or '%s_store' %storeCode,storeType=storeType,
                            parentStore=parentStore,handler=handler,**kwargs)
                            
    def multibutton_item(self,code,caption=None,**kwargs):
        return self.child('multibutton_item',code=code,caption=caption or code,**kwargs)
    
    def multibutton_plusitem(self,caption='+',deleteAction=False,ask=None,selectLast=None,**kwargs):
        return self.child('multibutton_item',code='plus_item',
                            sticky=False,deleteAction=deleteAction,
                            action="this.getParentNode().publish('appendItem',objectUpdate({selectLast:selectLast},_askResult));",
                            caption=caption,ask=ask,selectLast=selectLast,**kwargs)
    

    def multibutton_store(self,table=None,**kwargs):
        return self.child('multibutton_store',childname='itemsStore',table=table,**kwargs)

    def treegrid_column(self,field,**kwargs):
        return self.child('treegrid_column',field=field,**kwargs)  

    def treeframe_column(self,field,**kwargs):
        return self.child('treeframe_column',field=field,**kwargs)  

    def quickgrid(self,value,childname='grid',**kwargs):
        return self.child('quickgrid',value=value,childname=childname,**kwargs)

    def quickgrid_column(self,field,**kwargs):
        return self.child('quickgrid_column',field=field,**kwargs)  

    def quickgrid_selectionstore(self,table=None,**kwargs):
        return self.child('quickgrid_selectionstore',table=table,**kwargs) 

    def quickgrid_tools(self,tools,position=None,**kwargs):
        return self.child('quickgrid_tools',tools=tools,position=position,**kwargs) 

    def formstore_handler(self, action, handler_type=None, **kwargs):
        """TODO Return the formstore handler
        
        :param action: TODO
        :param handler_type: TODO"""
        return self.child('formstore_handler',childname=action,action=action,handler_type=handler_type,**kwargs)
        
    def formstore_handler_addcallback(self, cb, **kwargs):
        """TODO
        
        :param cb: TODO"""
        self.child('callBack',childcontent=cb,**kwargs)
        return self


    def iframe(self, childcontent=None, main=None, **kwargs):
        """Create an :ref:`iframe` and returns it
        
        :param childcontent: the html content
        :param main: TODO"""
        if main:
            self.attributes.update(dict(overflow='hidden'))
            kwargs['height'] = '100%'
            kwargs['width'] = '100%'
            kwargs['border'] = 0
        parent = self
        if self.page.isMobile:
            parent = parent.div(_class='scroll-wrapper')
        return parent.htmlChild('iframe', childcontent=childcontent, main=main, **kwargs)
    
    def htmliframe(self,**kwargs):
        """Create an :ref:`iframe` and returns it
        
        :param childcontent: the html content
        :param main: TODO"""
        parent = self
        if self.page.isMobile:
            parent = parent.div(_class='scroll-wrapper')
        return parent.child('htmliframe', **kwargs)
    

    def flexbox(self,direction=None,wrap=None,align_content=None,
                justify_content=None,align_items=None,
                justify_items=None,**kwargs):
        """Create a flexbox container for flexible layout of child elements.

        The flexbox container uses CSS Flexbox layout to arrange child elements in a flexible,
        responsive manner. It provides powerful alignment and distribution capabilities.

        Args:
            direction (str): Main axis direction for flex items.
                           - 'row': Left to right (default)
                           - 'column': Top to bottom
                           - 'row-reverse': Right to left
                           - 'column-reverse': Bottom to top

            wrap (bool or str): Whether flex items should wrap to next line.
                              - True/'wrap': Items wrap onto multiple lines
                              - False/'nowrap': Items stay on single line (default)
                              - 'wrap-reverse': Items wrap in reverse order

            align_content (str): Aligns lines when there is extra space on cross axis.
                               - 'flex-start': Lines packed to start
                               - 'flex-end': Lines packed to end
                               - 'center': Lines centered
                               - 'space-between': Lines evenly distributed
                               - 'space-around': Lines with equal space around
                               - 'stretch': Lines stretch to fill container (default)

            justify_content (str): Aligns items along main axis.
                                 - 'flex-start': Items packed to start (default)
                                 - 'flex-end': Items packed to end
                                 - 'center': Items centered
                                 - 'space-between': Items evenly distributed
                                 - 'space-around': Items with equal space around
                                 - 'space-evenly': Items with equal space between

            align_items (str): Aligns items along cross axis.
                             - 'flex-start': Items aligned to start
                             - 'flex-end': Items aligned to end
                             - 'center': Items centered
                             - 'baseline': Items aligned to baseline
                             - 'stretch': Items stretch to fill (default)

            justify_items (str): Justifies items within their area (grid-specific).

            **kwargs: Additional HTML/CSS attributes (e.g., height, width, border, padding)

        Returns:
            GnrDomSrcNode: The flexbox container node

        Example:
            # Simple horizontal flexbox
            box = pane.flexbox(direction='row', justify_content='space-between')
            box.div('Item 1')
            box.div('Item 2')
            box.div('Item 3')

            # Vertical flexbox with wrapping
            box = pane.flexbox(direction='column', wrap=True, height='200px')
            for i in range(10):
                box.div(f'Item {i}', height='30px')

            # Centered content
            box = pane.flexbox(justify_content='center', align_items='center',
                              height='100%')
            box.div('Centered content')

        See Also:
            - gridbox(): For grid-based layouts
            - borderContainer(): For region-based layouts
        """
        return self.child('flexbox',direction=direction, wrap=wrap,
                          align_content=align_content,justify_content=justify_content,
                          align_items=align_items,justify_items=justify_items,**kwargs)

    def expandbox(self, title=None, open=None, animate=None,
                  minimal=None, locked=None, **kwargs):
        """Create an expandable/collapsible container based on HTML5 details/summary.

        The expandbox widget wraps content in a native <details> element with a
        <summary> header. It supports CSS animations and reactive open/close binding.

        Args:
            title (str): The text displayed in the summary header.
            open (bool): Whether the box starts expanded. Default False.
            animate (bool): Enable smooth CSS transition on open/close.
            minimal (bool): Use minimal style (no border, no header background).
            locked (bool): Disable toggle — keeps current open/close state.
                           The marker is hidden and the header is not clickable.
            **kwargs: Additional attributes. Prefix with title_* for summary
                      styling and content_* for content div styling.

        Returns:
            GnrDomSrcNode: The expandbox container node.

        Example:
            box = pane.expandbox(title='Details', open=True, animate=True)
            fb = box.formbuilder(cols=2)
            fb.textbox(value='^.name', lbl='Name')
        """
        return self.child('expandbox', title=title, open=open,
                          animate=animate, minimal=minimal,
                          locked=locked, **kwargs)

    def gridbox(self,columns=None,align_content=None,justify_content=None,
                align_items=None,justify_items=None,table=None,**kwargs):
        """Create a gridbox container for two-dimensional grid-based layouts.

        The gridbox container uses CSS Grid layout to arrange child elements in a two-dimensional
        grid system with rows and columns. It provides powerful control over item positioning,
        sizing, and alignment, making it ideal for complex layouts, forms, and dashboards.

        Args:
            columns (int or str): Number of columns or explicit column definition.
                                - int: Number of equal-width columns (e.g., 3)
                                - str: CSS grid-template-columns value (e.g., '1fr 2fr 1fr')
                                If not specified, uses auto-placement.

            align_content (str): Aligns the grid within the container when there's extra space.
                               - 'start': Grid aligned to start
                               - 'end': Grid aligned to end
                               - 'center': Grid centered
                               - 'stretch': Grid stretches to fill (default)
                               - 'space-between': Space distributed between rows
                               - 'space-around': Space around each row
                               - 'space-evenly': Equal space between all rows

            justify_content (str): Aligns the grid horizontally within the container.
                                 - 'start': Grid aligned to start
                                 - 'end': Grid aligned to end
                                 - 'center': Grid centered
                                 - 'stretch': Grid stretches to fill (default)
                                 - 'space-between': Space distributed between columns
                                 - 'space-around': Space around each column
                                 - 'space-evenly': Equal space between all columns

            align_items (str): Aligns items vertically within their grid cell.
                             - 'start': Items aligned to cell start
                             - 'end': Items aligned to cell end
                             - 'center': Items centered in cell
                             - 'stretch': Items stretch to fill cell (default)

            justify_items (str): Aligns items horizontally within their grid cell.
                               - 'start': Items aligned to cell start
                               - 'end': Items aligned to cell end
                               - 'center': Items centered in cell
                               - 'stretch': Items stretch to fill cell (default)

            table (str): Optional table name for integration with Genro data handling.
                        Defaults to page.maintable if not specified.

            **kwargs: Additional attributes:
                     - gap (str): Spacing between grid items (e.g., '10px', '1em')
                     - column_gap (str): Horizontal spacing between columns
                     - row_gap (str): Vertical spacing between rows
                     - item_height (str): Default height for grid items
                     - item_border (str): Border applied to all items
                     - item_side (str): Label position for labledBox items ('top', 'left', etc.)

        Returns:
            GnrDomSrcNode: The gridbox container node

        Grid Item Attributes:
            Child elements can use these attributes for positioning:
            - colspan (int): Number of columns the item spans
            - rowspan (int): Number of rows the item spans

        Example:
            # Simple 3-column grid
            grid = pane.gridbox(columns=3, gap='10px')
            grid.div('Item 1')
            grid.div('Item 2')
            grid.div('Item 3', colspan=2)  # Spans 2 columns
            grid.div('Item 4')

            # Explicit column widths
            grid = pane.gridbox(columns='200px 1fr 2fr', row_gap='15px')
            grid.div('Sidebar', height='100%')
            grid.div('Content')
            grid.div('Main area')

            # Form layout with gridbox
            form = pane.gridbox(columns=2, gap='10px')
            form.textbox(value='^.name', lbl='Name')
            form.textbox(value='^.surname', lbl='Surname')
            form.textbox(value='^.email', lbl='Email', colspan=2)

            # Dashboard with different sized sections
            dashboard = pane.gridbox(columns=3, gap='20px', height='100%')
            dashboard.labledBox('Stats', colspan=2).borderContainer()
            dashboard.labledBox('Quick Actions')
            dashboard.labledBox('Recent Activity', colspan=3)

            # Centered grid
            grid = pane.gridbox(columns=4, justify_content='center',
                               align_items='center', height='400px')
            for i in range(8):
                grid.div(f'Cell {i}', border='1px solid #ccc')

        See Also:
            - flexbox(): For one-dimensional flexible layouts
            - formbuilder(): For traditional form layouts
            - labledBox(): For labeled containers within gridbox
        """
        return self.child('gridbox',columns=columns,table=table or self.page.maintable,
                          align_content=align_content,justify_content=justify_content,
                          align_items=align_items,justify_items=justify_items
                          ,**kwargs)
    
    def labledbox(self,label=None,**kwargs):
        return self.child('labledbox',label=label,**kwargs)


    def htmlform(self,childcontent=None,**kwargs):
        return self.htmlChild('form', childcontent=childcontent, **kwargs)

    def h1(self, childcontent=None, **kwargs):
        return self.htmlChild('h1', childcontent=childcontent, **kwargs)
        
    def h2(self, childcontent=None, **kwargs):
        return self.htmlChild('h2', childcontent=childcontent, **kwargs)
        
    def h3(self, childcontent=None, **kwargs):
        return self.htmlChild('h3', childcontent=childcontent, **kwargs)
        
    def h4(self, childcontent=None, **kwargs):
        return self.htmlChild('h4', childcontent=childcontent, **kwargs)
        
    def h5(self, childcontent=None, **kwargs):
        return self.htmlChild('h5', childcontent=childcontent, **kwargs)
        
    def h6(self, childcontent=None, **kwargs):
        return self.htmlChild('h6', childcontent=childcontent, **kwargs)
        
    def li(self, childcontent=None, **kwargs):
        return self.htmlChild('li', childcontent=childcontent, **kwargs)
        
    def td(self, childcontent=None, **kwargs):
        return self.htmlChild('td', childcontent=childcontent, **kwargs)
        
    def th(self, childcontent=None, **kwargs):
        return self.htmlChild('th', childcontent=childcontent, **kwargs)
        
    def span(self, childcontent=None, **kwargs):
        return self.htmlChild('span', childcontent=childcontent, **kwargs)
        
    def pre(self, childcontent=None, **kwargs):
        return self.htmlChild('pre', childcontent=childcontent, **kwargs)
        
    def div(self, childcontent=None, **kwargs):
        return self.htmlChild('div', childcontent=childcontent, **kwargs)
        
    def style(self,childcontent=None,**kwargs):
        return self.htmlChild('style', childcontent=childcontent, **kwargs)

    def details(self, childcontent=None, **kwargs):
        return self.htmlChild('details', childcontent=childcontent, **kwargs)

    def summary(self, childcontent=None, **kwargs):
        return self.htmlChild('summary', childcontent=childcontent, **kwargs)

    def a(self, childcontent=None, **kwargs):
        return self.htmlChild('a', childcontent=childcontent, **kwargs)
        
    def dt(self, childcontent=None, **kwargs):
        return self.htmlChild('dt', childcontent=childcontent, **kwargs)
        
    def option(self, childcontent=None, **kwargs):
        return self.child('option', childcontent=childcontent, **kwargs)
        
    def caption(self, childcontent=None, **kwargs):
        return self.htmlChild('caption', childcontent=childcontent, **kwargs)
        
    def button(self, caption=None, **kwargs):
        return self.child('button', caption=caption, **kwargs)

    def lightbutton(self, innerHTML=None, **kwargs):
        return self.child('lightbutton', innerHTML=innerHTML, **kwargs)

    def semaphore(self, value=None,  **kwargs):
        return self.child('div', innerHTML=value, dtype='B', format='semaphore', **kwargs)

    def errorPane(self, message, **kwargs):
        """Render a centered error pane with sad logo and message."""
        cp = self.contentPane(overflow='hidden',
            style='display:flex; align-items:center; justify-content:center; flex-direction:column; height:100%;',
            **kwargs)
        cp.img(src='/_rsrc/common/css_icons/svg/16/genrologo_sad.svg',
               height='64px', opacity='.5', margin_bottom='12px')
        cp.div(message, _class='selectable',
               style='color:#888; font-size:13px; text-align:center; max-width:400px; line-height:1.5;')
        return cp

   #def column(self, label='', field='', expr='', name='', **kwargs):
   #    if not 'columns' in self:
   #        self['columns'] = Bag()
   #    if not field:
   #        field = label.lower()
   #    columns = self['columns']
   #    name = 'C_%s' % str(len(columns))
   #    columns.setItem(name, None, label=label, field=field, expr=expr, **kwargs)
        
    def tooltip(self, label='', **kwargs):
        """Create a :ref:`tooltip` and return it
        
        :param label: the tooltip text"""
        return self.child('tooltip', label=label, **kwargs)
        
    def data(self, *args, **kwargs):
        """Create a :ref:`data` and returns it. ``data`` allows to define
        variables from server to client
        
        :param *args: args[0] includes the path of the value, args[1] includes the value
        :param **kwargs: in the kwargs you can insert the ``_serverpath`` attribute. For more
                           information, check the :ref:`data_serverpath` example"""
        value = None
        className = None
        path = None
        if len(args) == 1:
            if not kwargs:
                value = args[0]
                path = None
            else:
                path = args[0]
                value = None
        elif len(args) == 0 and kwargs:
            path = None
            value = None
        elif len(args) > 1:
            value = args[1]
            path = args[0]
        if isinstance(value, dict):
            value = Bag(value)
        if isinstance(value, Bag):
            className = 'bag'
        serverpath = kwargs.pop('serverpath',None) or kwargs.pop('_serverpath',None)

        if serverpath:
            self.page.addToContext(serverpath=serverpath,value=value,attr=kwargs)
            kwargs['serverpath'] = serverpath
        #shared_id = kwargs.pop('shared_id',None)
        #if shared_id:
        #    shared_expire = kwargs.pop('shared_expire',0)
        #    self.page.asyncServer.subscribeToSharedObject(shared_id=shared_id,page=page,expire=shared_expire)
#
        return self.child('data', __cls=className,childcontent=value,_returnStruct=False, path=path, **kwargs)
        
    def script(self, content='', **kwargs):
        """Handle the <script> html tag and return it
        
        :param content: the <script> content"""
        return self.child('script', childcontent=content, **kwargs)
    
    def bagField(self,value=None,method=None,**kwargs):
        return self.child('bagField',value=value,methodname=method,**kwargs)
    
    def grouplet(self,value=None,handler=None,**kwargs):
        return self.child('grouplet',value=value,handler=handler,**kwargs)

    def groupletform(self,value=None,handler=None,**kwargs):
        return self.child('groupletform',value=value,handler=handler,**kwargs)

    def remote(self, method=None, lazy=True, cachedRemote=None,**kwargs):
        """TODO
        
        :param method: TODO
        :param lazy: boolean. TODO"""
        if callable(method):
            handler = method
        else:
            handler = self.page.getPublicMethod('remote', method)
        if handler:
            kwargs_copy = copy(kwargs)
            parentAttr = self.parentNode.getAttr()
            parentAttr['remote'] = 'remoteBuilder'
            parentAttr['remote_handler'] = method
            if cachedRemote:
                parentAttr['_cachedRemote'] = cachedRemote
            for k, v in list(kwargs.items()):
                if k.endswith('_path'):
                    v = u'§%s' % v
                parentAttr['remote_%s' % k] = v
                kwargs.pop(k)
            if not lazy:
                onRemote = kwargs_copy.pop('_onRemote', None)
                if onRemote:
                    self.dataController(onRemote, _onStart=True)
                handler(self, **kwargs_copy)
                
    def func(self, name, pars='', funcbody=None, **kwargs):
        """TODO
        
        :param name: TODO
        :param pars: TODO
        :param funcbody: TODO"""
        if not funcbody:
            funcbody = pars
            pars = ''
        return self.child('func', childname=name, pars=pars, childcontent=funcbody, **kwargs)
        
    def connect(self, event='', pars='', funcbody=None, **kwargs):
        """TODO
        
        :param event: TODO
        :param pars: TODO
        :param funcbody: TODO"""
        if not (funcbody and pars):
            funcbody = event
            event = ''
            pars = ''
        elif not funcbody:
            funcbody = pars
            pars = ''
        return self.child('connect', event=event, pars=pars, childcontent=funcbody, **kwargs)
        
    def subscribe(self, what, event, func=None, **kwargs):
        """TODO
        
        :param what: TODO
        :param event: TODO
        :param func: TODO"""
        objPath = None
        if not isinstance(what, str):
            objPath = what.fullpath
            what = None
        return self.child('subscribe', obj=what, objPath=objPath, event=event, childcontent=func, **kwargs)
        


    def css(self, rule, styleRule=''):
        """Handle the CSS rules
        
        :param rule: dict or list of CSS rules
        :param styleRule: TODO"""
        if ('{' in rule):
            styleRule = rule
            rule = styleRule.split('{')[0]
            rule = rule.strip()
        else:
            if not styleRule.endswith(';'):
                styleRule = styleRule + ';'
            styleRule = '%s {%s}' % (rule, styleRule)
        return self.child('css', childcontent=styleRule)
        
    def styleSheet(self, cssText=None, cssTitle=None, href=None):
        """Create the styleSheet
        
        :param cssText: TODO
        :param cssTitle: TODO
        :param href: TODO"""
        self.child('stylesheet',childname=None, childcontent=cssText, href=href, cssTitle=cssTitle)
        
    def cssrule(self, selector=None, **kwargs):
        """TODO"""
        selector_replaced = selector.replace('.', '_').replace('#', '_').replace(' ', '_')
        self.child('cssrule',childname=selector_replaced, selector=selector, **kwargs)
        
    def macro(self, name='', source='', **kwargs):
        """TODO
        
        :param name: TODO
        :param source: TODO"""
        return self.child('macro', childname=name, childcontent=source, **kwargs)
        
    def input(self, value=None, **kwargs):
        return self.child('input', value=value, **kwargs)
    
    def getMainFormBuilder(self):
        return getattr(self.parentNode,'_mainformbuilder',None)

    def getFormBuilder(self,fbname=None,table=None):
        fbname = fbname if not table else '%s:%s' %(table,fbname)
        result = self.getNodeByAttr('fbname',fbname) or self.getNodeByAttr('formletCode',fbname)
        if result:
            return result.value.getItem('#0')
        
    def mobileFormBuilder(self,margin_right=None,_class=None,**kwargs):
        margin_right = margin_right or '10px'
        box = self.div(margin_right=margin_right)
        fld_width='100%'
        if kwargs.get('cols',1)>1:
            fld_width = f'calc(100% - {margin_right})'
        pars = dict(border_spacing='8px 0px', 
                        width='100%',fld_width=fld_width,lblpos='T',
                        lbl_text_align='left',lbl_font_size='.8em',
                        lbl_padding_top='4px',enableZoom=False,
                        lbl_font_weight='bold',fldalign='left',
                        fld_html_label=True,
                        _class=_class or 'mobilefields',
                        formlet=False)
        pars.update(kwargs)
        return box.formbuilder(**pars)
    

    def setHelperData(self,table=None,name=None,**kwargs):
        data,kw = self.page.getHelperData(table=table,name=name)
        if kw.get('in_cache'):
            return
        return self.page.pageSource().data(f"gnr.helpers.{kw['path']}",data)
       #return self.page.pageSource().child('dataRemote', path=f"gnr.helpers.{kw['path']}", 
       #                                    method='getHelperData',
       #                                    childcontent=childcontent,_resolved=True, 
       #                                    table=table,name=name)


    def formbuilder(self,*args,**kwargs):
        dbtable = kwargs.get('table') 
        if not dbtable:
            dbtable = kwargs.get('dbtable') or self.getInheritedAttributes().get('table')
            kwargs['table'] = dbtable
        defaultUseFormlet = self.page.pageOptions.get('useFormlet') or \
                            self.page.getPreference('theme.use_formlets',pkg='sys')
        if dbtable and not defaultUseFormlet:
            useFormletCb = getattr(self.page.db.table(dbtable),'useFormlet',None)
            if useFormletCb:
                defaultUseFormlet = useFormletCb()

        kwFormlet = kwargs.get('formlet')
        if kwFormlet is not False and defaultUseFormlet:
            kwargs.setdefault('item_lbl_side','left')
            return self.formbuilder_formlet(*args,**kwargs)
        else:
            return self.formbuilder_table(*args,**kwargs)
        
    def formlet(self,columns=None,table=None,formletCode=None,
                formletclass='formlet',_class=None,**kwargs):
        formNode = self.parentNode.attributeOwnerNode('formId') if self.parentNode else None
        excludeCols = kwargs.pop('excludeCols',None)
        if excludeCols:
            raise NotImplementedError('Not implemented in formlet')
        if formNode:
            table = table or formNode.attr.get('table')

        # Promote static item_* to their unprefixed form on the gridbox so
        # that child fields can pick them up via getInheritedAttributes()
        # before gridbox.onChildBuilding copies _items_attr on them
        # (buildLblWrapper runs *before* the child has been touched).
        # Reactive bindings (^...) must NOT be promoted: they would land on
        # the gridbox as unhandled reactive attrs and trigger rebuild loops.
        item_params = dictExtract(kwargs, 'item_', pop=False, slice_prefix=True)
        for param_name, value in item_params.items():
            if param_name in kwargs:
                continue
            if isinstance(value, str) and value.startswith('^'):
                continue
            kwargs[param_name] = value

        result =  self.gridbox(columns=columns,
                               table=table,
                            formletCode=formletCode,
                            _class=_class or f'gnrgridbox {formletclass}',**kwargs)
        if formNode:
            if not hasattr(formNode,'_mainformbuilder'):
                formNode._mainformbuilder = result
        return result
        
    def formbuilder_formlet(self, cols=1, table=None, formlet=None, lblpos='L', **kwargs):
        """Formlet-based backend for :meth:`formbuilder` when the *use_formlets* preference is active.

        Translates legacy ``formbuilder`` parameters into the :meth:`formlet` / gridbox
        attribute convention (``item_lbl_*``, ``item_fld_*``, …) and delegates to
        :meth:`formlet`.

        :param cols: number of grid columns (default 1)
        :param table: dotted table name (e.g. ``'myapp.mytable'``); falls back to page maintable
        :param formlet: formlet code to load a pre-defined formlet definition
        :param lblpos: legacy label-position shorthand – ``'L'`` (left), ``'T'`` (top),
                       ``'R'`` (right), ``'B'`` (bottom).  Converted to ``item_lbl_side``
                       unless that kwarg is already present.
        :param kwargs: forwarded to :meth:`formlet`; any ``lbl_*`` / ``fld_*`` / ``row_*``
                       prefixed keys are automatically promoted to their ``item_*`` equivalents.
        """
        commonPrefix = ('lbl_', 'fld_', 'row_', 'tdf_', 'tdl_')
        commonKwargs = {f'item_{k}': kwargs.pop(k) for k in list(kwargs.keys()) if len(k) > 4 and k[0:4] in commonPrefix}
        commonKwargs.update(dictExtract(kwargs, 'item_', pop=False, slice_prefix=False))
        kwargs.update(commonKwargs)

        if lblpos and 'item_lbl_side' not in kwargs:
            lblpos_map = {'L': 'left', 'T': 'top', 'R': 'right', 'B': 'bottom'}
            kwargs['item_lbl_side'] = lblpos_map.get(lblpos, 'left')

        return self.formlet(columns=cols, table=table or self.page.maintable,
                            formletCode=formlet, **kwargs)


        
    def formbuilder_table(self, cols=1, table=None, tblclass='formbuilder',
                    lblclass='gnrfieldlabel', lblpos='L',byColumn=None,
                    _class='', fieldclass='gnrfield',
                    colswidth=None,
                    lblalign=None, lblvalign='top',
                    fldalign=None, fldvalign='top', disabled=False,
                    rowdatapath=None, head_rows=None,spacing=None,boxMode=None,
                    formlet=None,**kwargs):
        """In :ref:`formbuilder` you can put dom and widget elements; its most classic usage is to create
        a :ref:`form` made by fields and layers, and that's because formbuilder can manage automatically
        fields and their positioning
        
        :param cols: set the number of columns
        :param table: the :ref:`database table <table>` name on which the query will be executed,
                      in the form ``packageName.tableName`` (packageName is the name of the
                      :ref:`package <packages>` to which the table belongs to)
        :param tblclass: the standard class for the formbuilder. Default value is ``'formbuilder'``,
                         that actually it is the unique defined CSS class
        :param lblclass: set CSS label style
        :param lblpos: set label position: ``L``: set label on the left side of text field
                       ``T``: set label on top of text field
        :param _class: for CSS style
        :param fieldclass: the CSS class appended to every formbuilder's child
        :param lblalign: Set horizontal label alignment (It seems broken... TODO)
        :param lblvalign: set vertical label alignment
        :param fldalign: set field horizontal align
        :param fldvalign: set field vertical align
        :param disabled: If ``True``, user can't act on the object (write, drag...). For more information,
                         check the :ref:`disabled` attribute
        :param rowdatapath: TODO
        :param head_rows: TODO
        :param **kwargs: for the complete list of the ``**kwargs``, check the :ref:`fb_kwargs` section"""
        if spacing:
            h_padding = float((kwargs.get('border_spacing') or '6px').replace('px',''))/2
            kwargs['border_spacing'] = '0px'
            v_padding = float(spacing)/2
            padding = '%spx %spx %spx %spx' %(v_padding,h_padding,v_padding,h_padding)
            kwargs['tdf_padding'] = padding
            kwargs['tdl_padding'] = padding

        dbtable = table or kwargs.get('dbtable') or self.getInheritedAttributes().get('table') or self.page.maintable
        if kwargs.get('fbname'):
            kwargs['fbname'] = kwargs['fbname'] if not dbtable else '%s:%s' %(dbtable,kwargs['fbname'])
        commonPrefix = ('lbl_', 'fld_', 'row_', 'tdf_', 'tdl_')
        commonKwargs = {k:kwargs.pop(k) for k in list(kwargs.keys()) if len(k) > 4 and k[0:4] in commonPrefix}

        #commonKwargs = dict([(k, kwargs.pop(k)) for k in list(kwargs.keys()) if len(k) > 4 and k[0:4] in commonPrefix])
        tbl = self.child('table', _class='%s %s' % (tblclass, _class), **kwargs).child('tbody')
        formNode = self.parentNode.attributeOwnerNode('formId') if self.parentNode else None
        excludeCols = kwargs.pop('excludeCols',None)
        if formNode:
            if not hasattr(formNode,'_mainformbuilder'):
                formNode._mainformbuilder = tbl
            if formNode.attr.get('excludeCols'):
                excludeCols = formNode.attr.pop('excludeCols')
        
        tbl.fbuilder = GnrFormBuilder(tbl, cols=int(cols), dbtable=dbtable,
                                      lblclass=lblclass, lblpos=lblpos, lblalign=lblalign, fldalign=fldalign,
                                      fieldclass=fieldclass,
                                      lblvalign=lblvalign, fldvalign=fldvalign,
                                      rowdatapath=rowdatapath,
                                      head_rows=head_rows, 
                                      excludeCols=excludeCols,
                                      byColumn=byColumn,colswidth=colswidth,
                                      boxMode=boxMode,
                                      commonKwargs=commonKwargs)
        
        inattr = self.getInheritedAttributes()
        if hasattr(self.page,'_legacy'):
            tbl.childrenDisabled = disabled
        if colswidth:
            colswidth = colswidth.split(',')
            if len(colswidth)==1:
                colsvalue=colswidth[0]
                if colsvalue == 'auto':
                    x = 100. / cols
                    colsvalue ='%s%%' % x
                colswidth = [colsvalue]

            for w in range(cols):
                k=w if w <len(colswidth) else len(colswidth) -1
                tbl.div(tdf_width=colswidth[k],tdl_height='0px', tdl_border='0',tdf_border='0', tdf_height='0px',min_height='0px', padding_top='0px')

        return tbl
        
    def place(self, fields):
        """TODO
        
        :param fields: TODO"""
        if hasattr(self, 'fbuilder'):
            self.fbuilder.setFields(fields)
            
    def getField(self, fld):
        """TODO
        
        :param fld: TODO"""
        result = {}
        if '.' in fld:
            x = fld.split('.')
            fld = x.pop()
            tblobj = self.page.db.table('.'.join(x), pkg=self.page.packageId)
        else:
            tblobj = self.tblobj
            result['value'] = '^.%s' % fld
            
        fieldobj = tblobj.column(fld)
        if fieldobj is None:
            raise GnrDomSrcError('Not existing field %s' % fld)
        dtype = result['dtype'] = fieldobj.dtype
        result['lbl'] = fieldobj.name_long
        result['size'] = 20
        fieldattr = fieldobj.attributes
        if 'checkpref' in fieldattr:
            result['checkpref'] = fieldattr['checkpref']
            result.update(dictExtract(fieldattr,'checkpref_'))

        result.update(dictExtract(fieldattr,'validate_'))
        relcol = fieldobj.relatedColumn()
        if relcol != None:
            lnktblobj = relcol.table
            linktable_attr = lnktblobj.attributes
            if linktable_attr.get('checkpref'):
                result['checkpref'] = linktable_attr['checkpref']
                result.update(dictExtract(linktable_attr,'checkpref_'))
            linktable = lnktblobj.fullname
            result['tag'] = 'DbSelect'
            result['dbtable'] = linktable
            result['dbfield'] = lnktblobj.rowcaption
            result['recordpath'] = ':@*'
            result['keyfield'] = relcol.name
            result['_class'] = 'linkerselect'
            if hasattr(lnktblobj, 'zoomUrl'):
                zoomPage = lnktblobj.zoomUrl()
                
            else:
                zoomPage = linktable.replace('.', '/')
            result['lbl_href'] = '^.%s?zoomUrl' % fld
            result['zoomPage'] = zoomPage
        #elif attr.get('mode')=='M':
        #    result['tag']='bagfilteringtable'
        elif dtype == 'A':
            result['size'] = fieldobj.print_width or 10
            result['tag'] = 'input'
            result['_type'] = 'text'
        elif dtype == 'B':
            result['tag'] = 'checkBox'
        elif dtype == 'T':
            result['size'] = fieldobj.print_width or 40
            result['tag'] = 'input'
        elif dtype == 'D':
            result['tag'] = 'dropdowndatepicker'
        else:
            result['tag'] = 'input'
            
        return result
