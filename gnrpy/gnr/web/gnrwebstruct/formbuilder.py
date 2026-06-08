#-*- coding: utf-8 -*-

#--------------------------------------------------------------------------
# package       : GenroPy web - see LICENSE for details
# module        : Genro Web structures - GnrFormBuilder
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

from gnr.core.gnrdict import dictExtract


class GnrFormBuilder(object):
    """The class that handles the creation of the :ref:`formbuilder` widget"""
    def __init__(self, tbl, cols=None, dbtable=None, fieldclass=None,
                 lblclass=None, lblpos='L',byColumn=None, lblalign=None, fldalign=None,
                 lblvalign='top', fldvalign='top', rowdatapath=None, head_rows=None,
                 excludeCols=None, colswidth=None,boxMode=False,commonKwargs=None):
        self.commonKwargs = commonKwargs or {}
        self.lblalign = lblalign or {'L': 'right', 'T': 'left'}[lblpos] # jbe?  why is this right and not left?
        self.fldalign = fldalign or {'L': 'left', 'T': 'center'}[lblpos]
        self.boxMode = boxMode
        self.lblvalign = lblvalign
        self.fldvalign = fldvalign
        self.lblclass = lblclass or 'gnrfieldlabel' if not self.boxMode else None
        self.fieldclass = fieldclass 
        self.colswidth = colswidth
        self.colmax = cols
        self.lblpos = lblpos
        self.rowlast = -1
        self.byColumn = byColumn
        #self._tbl=weakref.ref(tbl)
        self._tbl = tbl
        self.maintable = dbtable
        if self.maintable:
            self.tblobj = self.page.db.table(self.maintable)
        self.rowcurr = -1
        self.colcurr = 0
        self.row = -1
        self.col = -1
        self.rowdatapath = rowdatapath
        self.head_rows = head_rows or 0
        self.field_list = []
        self.excludeCols = excludeCols.split(',') if excludeCols else []
        
    def br(self):
        #self.row=self.row+1
        self.col = 999
        return self.tbl
        
    def _get_page(self):
        return self.tbl.page
        
    page = property(_get_page)
            
    def _get_tbl(self):
        #return self._tbl()
        return self._tbl
        
    tbl = property(_get_tbl)
        
    def place(self, **fieldpars):
        """TODO"""
        if 'value' in fieldpars and fieldpars['value'].startswith('^.'):
            self.field_list.append(fieldpars['value'][2:])
        return self.setField(fieldpars)
        
    def setField(self, field, row=None, col=None):
        """TODO
        
        :param field: TODO
        :param row: TODO
        :param col: TODO
        """
        field = dict(field)
        if 'pos' in field:
            rc = ('%s,0' % field.pop('pos')).split(',')
            if rc[0] == '*':
                rc[0] = str(self.row)
            elif rc[0] == '+':
                rc[0] = str(self.row + 1)
            self.row, self.col = int(rc[0]), int(rc[1])
        elif ('pos_r' in field) or ('pos_c' in field):
            self.row = field.get('pos_r',self.row)
            self.col = field.get('pos_c',self.col)
        else:
            if row is None:
                row = self.row
                col = self.col
            if col < 0:
                col = self.colmax + col
            self.row, self.col = self.nextCell(row, col)
        if 'fld' in field:
            fld_dict = self.tbl.getField(field.pop('fld'))
            fld_dict.update(field)
            field = fld_dict
        return self._formCell(self.row, self.col, field)
        
    def setFields(self, fields, rowstart=0, colstart=0):
        """TODO
        
        :param fields: TODO
        :param rowstart: TODO
        :param colstart: TODO
        """
        for field in fields:
            self.setField(field)
                
    def _fillRows(self, r):
        if r > self.rowlast:
            for j in range(self.rowlast, r):
                self._formRow(j + 1)
                
    def setRowAttr(self, r, attrs):
        """TODO
        
        :param r: the row to set
        :param attrs: TODO
        """
        self._fillRows(r)
        if self.lblpos == 'L':
            return self.tbl.setAttr('r_%i' % r, attrs)
        else:
            return (self.tbl.setAttr('r_%i_l' % r, attrs), self.tbl.setAttr('r_%i_f' % r, attrs))
                
    def getRowNode(self, r):
        """TODO
        
        :param r: the row from which to get node
        """
        self._fillRows(r)
        if self.lblpos == 'L':
            return self.tbl.getNode('r_%i' % r)
        else:
            return (self.tbl.getNode('r_%i_l' % r), self.tbl.getNode('r_%i_f' % r))
                
    def getRow(self, r):
        """TODO
        
        :param r: the row to get
        """
        self._fillRows(r)
        if self.lblpos == 'L':
            return self.tbl['r_%i' % r]
        else:
            rl = self.tbl['r_%i_l' % r]
            rf = self.tbl['r_%i_f' % r]
            if r>=0 and not rl:
                rl.attributes['hidden'] = True
            return (rl,rf)
                
    def nextCell(self, r, c):
        """Get the current row (*r* attribute) and the current cell (*c* attribute)
        of the :ref:`struct` and return the correct next row and cell
        
        :param r: a row
        :param c: a cell
        """
        def nc(row, r, c):
            c = c + 1
            if c >= self.colmax:
                c = 0
                r = r + 1
                row = self.getRow(r)
            return row, r, c
                
        row = self.getRow(r)
        row, r, c = nc(row, r, c)
        if self.lblpos == 'L':
            while not 'c_%i_l' % c in list(row.keys()):
                row, r, c = nc(row, r, c)
        else:
            while not 'c_%i' % c in list(row[0].keys()):
                row, r, c = nc(row, r, c)
        return r, c
                
    def setRow(self, fields, row=None):
        """TODO
        
        :param fields: TODO
        :param row: TODO
        """
        colcurr = -1
        if row is None:
            row = self.rowcurr = self.rowcurr + 1
        if row > self.rowlast:
            for r in range(self.rowlast, row):
                self._formRow(r + 1)
        self._formRow(row)
                
        for f in fields:
            if not 'col' in f:
                col = colcurr = colcurr + 1
            else:
                col = int(f.pop('col'))
            if col <= self.colmax:
                self.setField(f, row, col)
                
    def _formRow(self, r):
        if self.rowdatapath and r >= self.head_rows:
            rdp = '.r_%i' % (r - self.head_rows, )
        else:
            rdp = None
        if self.lblpos == 'L':
            self.tbl.tr(childname='r_%i' % r, datapath=rdp)
                
        elif self.lblpos == 'T':
            self.tbl.tr(childname='r_%i_l' % r, datapath=rdp)
            self.tbl.tr(childname='r_%i_f' % r, datapath=rdp)
        self.rowlast = max(self.rowlast, r)
                
        for c in range(self.colmax):
            self._formCell(r, c)
                
    def _formCell(self, r, c, field=None):
        row = self.getRow(r)
        row_attributes = dict()
        td_field_attr = dict()
        td_lbl_attr = dict()
        lbl = ''
        lblvalue = None
        tag = None
        excludeCols = self.excludeCols
        rowspan, colspan = 1, 1
        lblalign, fldalign = self.lblalign, self.fldalign
        lblvalign, fldvalign = self.lblvalign, self.fldvalign
        lbl_kwargs = {}
        if self.colswidth=='auto':
            lbl_kwargs.setdefault('margin_left','5px')
        lblhref = None
        if field is not None:
            f = dict(self.commonKwargs)
            f.update(field)
            field = f
            lbl = field.pop('lbl', '')
            dbfield = field.get('dbfield')
            if dbfield and excludeCols and dbfield.split('.')[-1] in excludeCols:
                field.setdefault('hidden',True)
            if field.get('checkpref'):
                lbl_kwargs['checkpref'] = field['checkpref']
                lbl_kwargs.update(dictExtract(field,'checkpref_'))
            if 'hidden' in field and 'lbl_hidden' not in field and self.lblpos=='L':
                onCreating = field.get('onCreating') or ''
                field['onCreating'] = """
                    %s
                    this._startHidden = objectPop(arguments[0],'hidden');
                """ %onCreating
                onCreated = field.get('onCreated') or ''
                field['onCreated'] = """%s
                    this._hiddenTargets = [];
                    var tdNode = this.attributeOwnerNode('tag','td');
                    this._hiddenTargets.push(tdNode.domNode)
                    this._hiddenTargets.push(tdNode.getChild('parent/'+tdNode.label.replace('_f','_l')).domNode);
                    var hiddenGroup = this.attr.hiddenGroup;
                    if(hiddenGroup){
                        var tblNode = this.attributeOwnerNode('tag','table');
                        tblNode._hiddenGroups = tblNode._hiddenGroups || {};
                        tblNode._hiddenGroups[hiddenGroup] = this._hiddenTargets;
                    }
                    var that = this;
                    genro.src.onBuiltCall(function(){
                        that.setHidden(that._startHidden);
                        delete that._startHidden;
                    },1);
                """ %onCreated
            if field.get('hiddenGroup') and 'hidden' not in field:
                onCreated = field.get('onCreated') or ''
                field['onCreated'] = """%s
                    var hiddenGroup = this.attr.hiddenGroup;
                    var tblNode = this.attributeOwnerNode('tag','table');
                    var tdNode = this.getChild('parent');
                    var groupHiddenTargets = tblNode._hiddenGroups[hiddenGroup];
                    groupHiddenTargets.push(tdNode.domNode)
                    groupHiddenTargets.push(tdNode.getChild('parent/'+tdNode.label.replace('_f','_l')).domNode);
                """ %onCreated
            if lbl and '_valuelabel' not in field and not lbl.startswith('=='):  #BECAUSE IT CANNOT CALCULATE ON THE FIELD SOURCENODE SCOPE
                field['_valuelabel'] = lbl
            if 'lbl_href' in field:
                lblhref = field.pop('lbl_href')
                lblvalue = lbl
                lbl = None
            for k in list(field.keys()):
                attr_name = k[4:]
                if attr_name == 'class':
                    attr_name = '_class'
                if k.startswith('row_'):
                    row_attributes[attr_name] = field.pop(k)
                elif k.startswith('lbl_'):
                    lbl_kwargs[attr_name] = field.pop(k)
                elif k.startswith('fld_'):
                    v = field.pop(k)
                    if attr_name not in field:
                        field[attr_name] = v
                elif k.startswith('tdf_'):
                    td_field_attr[attr_name] = field.pop(k)
                elif k.startswith('tdl_'):
                    td_lbl_attr[attr_name] = field.pop(k)
               
            if field.pop('html_label',None) and field.get('dtype') =='B':
                field['label'] = lbl
                lbl = None
            lblalign, fldalign = field.pop('lblalign', lblalign), field.pop('fldalign', fldalign)
            lblvalign, fldvalign = field.pop('lblvalign', lblvalign), field.pop('fldvalign', fldvalign)
            tag = field.pop('tag', None)
            rowspan = int(field.pop('rowspan', '1'))
            cspan = int(field.pop('colspan', '1'))
            if cspan > 1:
                for cs in range(c + 1, c + cspan):
                    if ((self.lblpos == 'L') and ('c_%i_l' % cs in list(row.keys()))) or (
                    (self.lblpos == 'T') and ('c_%i' % cs in list(row[0].keys()))):
                        colspan = colspan + 1
                    else:
                        break
                        
        kwargs = {}
        if self.lblpos == 'L':
            if rowspan > 1:
                kwargs['rowspan'] = str(rowspan)
            lbl_kwargs.update(kwargs)
            lblvalign = lbl_kwargs.pop('vertical_align', lblvalign)
            lblalign = lbl_kwargs.pop('align', lblalign)
            if '_class' in lbl_kwargs:
                lbl_kwargs['_class'] = self.lblclass + ' ' + lbl_kwargs['_class']
            else:
                lbl_kwargs['_class'] = self.lblclass
            _tdl_cls = ('fb_lbl ' + td_lbl_attr.pop('_class', '')).strip()
            if lblhref:
                cell = row.td(childname='c_%i_l' % c, _class=_tdl_cls, childcontent=lbl, align=lblalign, vertical_align=lblvalign, **td_lbl_attr)
                if lblvalue:
                    lbl_kwargs['tabindex'] = -1 # prevent tab navigation to the zoom link
                    cell.a(childcontent=lblvalue, href=lblhref, **lbl_kwargs)
            else:
                if self.boxMode:
                    kwargs['lbl'] = lbl
                    for k,v in lbl_kwargs.items():
                        kwargs[f'lbl_{k}'] = v
                    row.td(childname='c_%i_l' % c, hidden=True)
                else:
                    cell = row.td(childname='c_%i_l' % c, _class=_tdl_cls, align=lblalign, vertical_align=lblvalign, **td_lbl_attr)
                    if lbl:
                        cell.div(childcontent=lbl, **lbl_kwargs)
            for k, v in list(row_attributes.items()):
                # TODO: warn if row_attributes already contains the attribute k (and it has a different value)
                row.parentNode.attr[k] = v
            if colspan > 1:
                kwargs['colspan'] = str(colspan * 2 - 1)
            kwargs.update(td_field_attr)
            td = row.td(childname='c_%i_f' % c, align=fldalign, vertical_align=fldvalign, _class='%s tag_%s' %(self.fieldclass,tag), **kwargs)
            if colspan > 1:
                for cs in range(c + 1, c + colspan):
                    row.delItem('c_%i_l' % cs)
                    row.delItem('c_%i_f' % cs)
            if rowspan > 1:
                for rs in range(r + 1, r + rowspan):
                    row = self.getRow(rs)
                    for cs in range(c, c + colspan):
                        row.delItem('c_%i_l' % cs)
                        row.delItem('c_%i_f' % cs)
        elif self.lblpos == 'T':
            if colspan > 1:
                kwargs['colspan'] = str(colspan)
            lbl_kwargs.update(kwargs)
            lblvalign = lbl_kwargs.pop('vertical_align', lblvalign)
            lblalign = lbl_kwargs.pop('align', lblalign)
            if '_class' in lbl_kwargs:
                lbl_kwargs['_class'] = self.lblclass + ' ' + lbl_kwargs['_class']
            else:
                lbl_kwargs['_class'] = self.lblclass
            
            row[0].td(childname='c_%i' % c, childcontent=lbl, align=lblalign, vertical_align=lblvalign, **lbl_kwargs)
            if lbl:
                row[0].attributes.pop('hidden',None)
            td = row[1].td(childname='c_%i' % c, align=fldalign, vertical_align=fldvalign, **kwargs)
            for k, v in list(row_attributes.items()):
                # TODO: warn if row_attributes already contains the attribute k (and it has a different value)
                row[0].parentNode.attr[k] = v
                row[1].parentNode.attr[k] = v
                
            if colspan > 1:
                for cs in range(c + 1, c + colspan):
                    row[0].delItem('c_%i' % cs)
                    row[1].delItem('c_%i' % cs)
                        
        if tag:
            field['placeholder'] = field.get('placeholder',field.pop('ghost', None))
            if self.byColumn and not 'tabindex' in field:
                field['tabindex'] = (c+1)*100+r+1
            obj = td.child(tag, **field)
            return obj
