#-*- coding: utf-8 -*-

#--------------------------------------------------------------------------
# package       : GenroPy web - see LICENSE for details
# module        : Genro Web structures - GnrGridStruct
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

from gnr.core.gnrbag import Bag
from gnr.core import gnrstring
from gnr.core.gnrdict import dictExtract
from gnr.core.gnrstructures import GnrStructData

from gnr.web.gnrwebstruct._helpers import cellFromField, _selected_defaultFrom


class GnrGridStruct(GnrStructData):
    """This class handles the creation of a :ref:`struct`"""
    
    def makeRoot(cls, page, maintable=None, source=None):
        """TODO
        
        :param cls: TODO
        :param page: TODO
        :param maintable: the :ref:`database table <table>` to which the :ref:`struct` refers to.
                          For more information, check the :ref:`maintable` section
        :param source: TODO
        """
        root = GnrStructData.makeRoot(source=source, protocls=cls)
        #root._page = weakref.ref(page)
        root._page = page
        root._maintable = maintable
        return root
        
    makeRoot = classmethod(makeRoot)
        
    def _get_page(self):
        #return self.root._page()
        return self.root._page
        
    page = property(_get_page)
        
    def _get_maintable(self):
        return self.root._maintable
        
    maintable = property(_get_maintable)
        
    def _get_tblobj(self):
        maintable = self.root.maintable
        if maintable:
            return self.page.db.table(maintable)
        else:
            return None #self.page.tblobj
                
    tblobj = property(_get_tblobj)
        
    def view(self, tableobj=None, **kwargs):
        """TODO
        
        :param tableobj: the :ref:`database table <table>` object"""
        self.tableobj = tableobj
        return self.child('view', **kwargs)
        
    def info(self, **kwargs):        
        return self.child('info',childname='info', **kwargs)

    def columnsets(self, **kwargs):        
        return self.child('columnsets',childname='columnsets', **kwargs)

    def rows(self, classes=None, cellClasses=None, headerClasses=None, **kwargs):
        """TODO
        
        :param classes: TODO
        :param cellClasses: TODO
        :param headerClasses: TODO"""
        return self.child('rows', classes=classes, cellClasses=cellClasses, headerClasses=headerClasses, **kwargs)
        
    def columnset(self,code=None,name=None,columns=None,**kwargs):
        columnsets = self
        if self.attributes['tag']=='rows':
            structroot = columnsets.parent.parent
            columnsets = structroot.getItem('info.columnsets')
            if not columnsets:
                info = structroot.getItem('info')
                if not info:
                    info = structroot.info()
                columnsets = info.columnsets()
        result = columnsets.child('columnset',code=code, name=name, childname=code,**kwargs)
        if columns:
            cellskw = dictExtract(kwargs,'cells_')
            for c in columns:
                defaultkw = dict(cellskw)
                tag = defaultkw.pop('tag','cell')
                c.update(defaultkw)
                getattr(result,tag)(**c)
        return result
    
    def _collist(self,code,values,dtype=None):
        columns = []
        dtype = dtype or 'T'
        if isinstance(values,str):
            for i,c in enumerate(values.split(',')):
                val,name = c.split(':')
                if '|' in name:
                    name = name.split('|')[1]
                columns.append(dict(field=f'{code}_{i+1:02}',name=name,value=self.page.catalog.fromText(val,dtype)))
        return columns 
        
    def radioButtonSet(self,code=None,name=None,values=None,dtype=None,columns=None,**kwargs):
        return self.columnset(code=code,name=name ,
                        cells_radioButton = code,
                        cells_tag='checkboxcolumn',
                        columns=columns or self._collist(code,values,dtype=dtype),**kwargs)
    
    def checkBoxSet(self,code=None,name=None,values=None,dtype=None,aggr=None,columns=None,**kwargs):
        return self.columnset(code=code,name=name ,
                        cells_checkBoxAggr = aggr,
                        cells_checkBox = code,
                        cells_tag='checkboxcolumn',
                        cells__customGetter="""function(rowdata,rowidx){
                            let result = rowdata[this.checkBox]? rowdata[this.checkBox].split(',').includes(this.assignedValue):false;
                            return result;
                        }""",
                        columns=columns or self._collist(code,values,dtype=dtype),**kwargs)



    def cell(self, field=None, name=None, width=None, dtype=None, classes=None, cellClasses=None, 
            headerClasses=None,**kwargs):
        """Return a :ref:`cell`
        
        :param field: TODO
        :param name: TODO
        :param width: the width of the cell
        :param dtype: the :ref:`datatype`
        :param classes: TODO
        :param cellClasses: TODO
        :param headerClasses: TODO"""
        if not self.page.application.allowedByPreference(**kwargs):
            return 
        if field and getattr(self,'tblobj',None):
            kwargs.setdefault('calculated',self.tblobj.column(field) is None)
        row = self
        parentAttributes = self.attributes
        if  parentAttributes['tag'] == 'columnset':
            row = self.parent.parent.parent.getItem('view_0.rows_0')
            kwargs['columnset'] = parentAttributes['code']
        return row.child('cell', childcontent='', field=field, name=name or field, width=width, dtype=dtype,
                          classes=classes, cellClasses=cellClasses, headerClasses=headerClasses,
                          **kwargs)
                          
    
    def checkboxcolumn(self,field=None,checkedId=None,radioButton=False,calculated=True,name=None,
                        checkedField=None,action=None,action_delay=None,
                        remoteUpdate=False,trueclass=None,falseclass=None,value=None,**kwargs):
        if not radioButton:
            field = field or '_checked'
        if field and getattr(self,'tblobj',None):
            calculated = self.tblobj.column(field) is None
        else:
            calculated = not remoteUpdate
        self.cell(field=field,checkBoxColumn=dict(checkedId=checkedId,radioButton=radioButton,checkedField=checkedField,action=action,
                                                  action_delay=action_delay,remoteUpdate=remoteUpdate,trueclass=trueclass,falseclass=falseclass),calculated=calculated,name=name,
                                                  assignedValue=value,
                                                  **kwargs)
        
    def checkboxcell(self, field=None, falseclass=None,
                     trueclass=None,nullclass=None, classes='row_checker', action=None, name=' ',
                     calculated=False, radioButton=False,threestate=None, **kwargs):
        """Return a :ref:`checkboxcell`
        
        :param field: TODO
        :param falseclass: the css class for the false state
        :param trueclass: the css class for the true state
        :param nullclass: the css class for the null state, the optional third state that you can
                          specify through the **threestate** parameter
        :param classes: TODO
        :param action: allow to execute a javascript callback. For more information, check the
                       :ref:`action_attr` page
        :param name: TODO
        :param calculated: boolean. TODO
        :param radioButton: boolean. TODO
        :param threestate: boolean. If ``True``, create a third state (the "null" state) besides the ``True``
                           and the ``False`` state"""
        if not field:
            field = '_checked'
            calculated = True
        falseclass = falseclass or ('checkboxOff' if not radioButton else falseclass or 'radioOff')
        trueclass = trueclass or ('checkboxOn' if not radioButton else trueclass or 'radioOn')
        
        threestate = threestate or False
        if threestate is True:
            nullclass = nullclass or ('checkboxOnOff' if not radioButton else nullclass or 'radioOnOff')
        elif threestate == 'disabled':
            nullclass = 'dimmed checkboxOnOff'
        elif threestate == 'hidden':
            nullclass = 'hidden'
        self.cell(field, name=name, format_trueclass=trueclass, format_falseclass=falseclass,format_nullclass=nullclass,
                  classes=classes, calculated=calculated, format_onclick="""
                                                                    var threestate ='%(threestate)s';
                                                                    var rowpath = '#'+this.widget.absIndex(kw.rowIndex);
                                                                    var sep = this.widget.datamode=='bag'? '.':'?';
                                                                    var valuepath=rowpath+sep+'%(field)s';
                                                                    var storebag = this.widget.storebag();                                                                    
                                                                    var blocked = this.form? this.form.isDisabled() : false;
                                                                    var checked = storebag.getItem(valuepath);
                                                                    if (blocked || ((checked===null) && (threestate=='disabled'))){
                                                                        return;
                                                                    }
                                                                    if(threestate=='True'){
                                                                        checked = checked===false?true:checked===true?null:false;
                                                                    }else{
                                                                        checked = !checked;
                                                                    }
                                                                    storebag.setItem(valuepath, checked);
                                                                    this.publish('checked_%(field)s',{row:this.widget.rowByIndex(kw.rowIndex),
                                                                                                      pkey:this.widget.rowIdByIndex(kw.rowIndex),
                                                                                                      checked:checked});
                                                                    %(action)s
                                                                    """ % dict(field=field, action=action or '',threestate=threestate)
                  , dtype='B', **kwargs)
                  

    def templatecell(self,field,name=None,template=None,table=None,**kwargs):
        table = table or self.tblobj.fullname
        tpl = self.page.loadTemplate('%s:%s' %(table,template))
        tplattr = tpl.getAttr('main')
        return self.cell(field,name=name,calculated=True,template_columns=('%(columns)s,%(virtual_columns)s' %tplattr).strip(','),template=template)


    def fieldcell(self, field, 
                _as=None, name=None, width=None, dtype=None,
                  classes=None, cellClasses=None, headerClasses=None,
                   zoom=False,template_name=None,table=None,**kwargs):
        tableobj = self.tblobj
        if table:
            tableobj = self.page.db.table(table)
            _as = field
            field = tableobj.pkey
            tbl_caption_field = tableobj.attributes.get('caption_field')
            caption_field = kwargs.get('caption_field') or '%s_caption' %_as
            kwargs['related_table'] = table
            kwargs['caption_field'] = caption_field
            kwargs['rowcaption'] = tbl_caption_field
            kwargs['relating_column'] = _as
            kwargs['related_column'] = tbl_caption_field


        if not tableobj:
            self.root._missing_table = True
            return
        fldobj = tableobj.column(field)
        cellpars = cellFromField(field,tableobj,checkPermissions=self.page.permissionPars)
        cellpars.update(kwargs)
        if cellpars.get('edit') and fldobj.sqlclass=='column' and fldobj.relatedTable() is not None:
            selected_kw = {}
            _selected_defaultFrom(fieldobj=fldobj,result=selected_kw)
            if selected_kw:
                if cellpars['edit'] is not True:
                    selected_kw.update(kwargs['edit'])
                cellpars['edit'] = selected_kw
        template_name = template_name or fldobj.attributes.get('template_name')
        if template_name:
            tpl = self.page.loadTemplate('%s:%s' %(tableobj.fullname,template_name))
            tplattr = tpl.getAttr('main')
            cellpars['template_columns'] = ('%(columns)s,%(virtual_columns)s' %tplattr).strip(',')
        loc = locals()
        for attr in ('name','width','dtype','classes','cellClasses','headerClasses'):
            cellpars[attr] = loc[attr] or cellpars.get(attr)
        if zoom:
            zoomtbl = fldobj.table
            relfldlst = tableobj.fullRelationPath(field).split('.')
            if len(relfldlst) > 1:
                if zoom is True:
                    ridx = -2
                else:
                    ridx = relfldlst.index('@%s' % zoom)
                zoomtbl = tableobj.column('.'.join(relfldlst[0:ridx + 1])).parent
                relfldlst[ridx] = relfldlst[ridx][1:]
                cellpars['zoom_pkey'] = cellpars.get('zoom_pkey') or '.'.join(relfldlst[0:ridx + 1])
            elif fldobj.relatedTable():
                zoomtbl = fldobj.relatedTable()
                cellpars['zoom_pkey'] = field
            if hasattr(zoomtbl.dbtable, 'zoomUrl'):
                zoomPage = zoomtbl.dbtable.zoomUrl()
                cellpars['zoom_page'] = zoomPage
            cellpars['zoom_table'] = zoomtbl.dbtable.fullname
        return self.cell(field=_as or field, **cellpars)

    def fields(self, columns, unit='em', totalWidth=None):
        """TODO
        
        :param columns: it represents the :ref:`columns` to be returned by the "SELECT"
                        clause in the traditional sql query. For more information, check the
                        :ref:`sql_columns` section
        :param unit: the field unit
        :param totalWidth: TODO
        
        r.fields('name/Name:20,address/My Addr:130px....')"""
        tableobj = self.tblobj
        if isinstance(columns, str):
            columns = columns.replace('\n', '').replace('\t', '')
            col_list = gnrstring.splitAndStrip(columns, ',')
            if '[' in columns:
                maintable = []
                columns = []
                for col in col_list:
                    if '[' in col:
                        tbl, col = col.split('[')
                        maintable = [tbl]
                    columns.append('.'.join(maintable + [col.rstrip(']')]))
                    if col.endswith(']'):
                        maintable = []
            else:
                columns = col_list
        fields = []
        names = []
        widths = []
        dtypes = []
        fld_kwargs = []
        wtot = 0
        for field in columns:
            field, width = gnrstring.splitAndStrip(field, sep=':', n=2, fixed=2)
            field, name = gnrstring.splitAndStrip(field, sep='/', n=2, fixed=2)
            fldobj = tableobj.column(field)
            if fldobj is None:
                raise Exception("Unknown field %s in table %s" % (
                field, tableobj.fullname)) # FIXME: use a specific exception class
            fields.append(field)
            names.append(name or fldobj.name_long)
            if r'%' in width:
                unit='%'
                width = width.replace('%','')
            width = int(width  or fldobj.print_width)
            widths.append(width)
            wtot = wtot + width
            dtypes.append(fldobj.dtype)
            fld_kwargs.append(dict()) #PROVVISORIO
            
        if totalWidth:
            for j, w in enumerate(widths):
                widths[j] = int(w * totalWidth/wtot)
        for j, field in enumerate(fields):
            #self.child('cell', field=field, childname=names[j], width='%i%s'%(widths[j],unit), dtype=dtypes[j])
            self.cell(field=field, name=names[j], width='%i%s' % (widths[j], unit), dtype=dtypes[j], **fld_kwargs[j])
            
    def getFieldNames(self, columns=None):
        """TODO
        
        :param columns: it represents the :ref:`columns` to be returned by the "SELECT"
                        clause in the traditional sql query. For more information, check the
                        :ref:`sql_columns` section"""
        if columns is None:
            columns = []
        for v, fld in self.digest('#v,#a.field'):
            if fld:
                if not fld[0] in ('$', '@'):
                    fld = '$%s' % fld
                columns.append(fld)
            if isinstance(v, Bag):
                v.getFieldNames(columns)
        return ','.join(columns)
        
    fieldnames = property(getFieldNames)
