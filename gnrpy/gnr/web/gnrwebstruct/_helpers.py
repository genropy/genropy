#-*- coding: utf-8 -*-

#--------------------------------------------------------------------------
# package       : GenroPy web - see LICENSE for details
# module        : Genro Web structures helpers
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


def _selected_defaultFrom(fieldobj=None,result=None):
    for c in fieldobj.table.columns.values():
        defaultFrom = c.attributes.get('defaultFrom')
        if not (defaultFrom and defaultFrom[1:].startswith(fieldobj.name)):
            continue
        colname = c.name
        pathlist = defaultFrom.split('.')
        if pathlist[-1].startswith('@'):
            pathlist.append(colname)
        colpath = pathlist[1:]
        key = pathlist[-1]
        value = f'.{colname}'
        if len(colpath)>1:
            value = f'{value}={".".join(colpath)}'
        result[f"selected_{key}"] = value

def cellFromField(field,tableobj,checkPermissions=None):
    kwargs = dict()
    fldobj = tableobj.column(field)
    if fldobj is None:
        raise Exception('Missing column {} in table {}'.format(field,tableobj.fullname))
    fldattr = dict(fldobj.attributes or dict())
        
    if (fldattr.get('cell_edit') or fldattr.get('edit'))\
         and fldobj.table.fullname!=fldobj.fullname:
        fldattr.pop('cell_edit',None)
        fldattr.pop('edit',None)
        
    
    if checkPermissions:
        fldattr.update(fldobj.getPermissions(**checkPermissions))
    if fldattr.get('checkpref'):
        kwargs['checkpref'] = fldattr.get('checkpref')
        kwargs.update(dictExtract(fldattr,'checkpref_'))

    if fldattr.get('user_forbidden'):
        kwargs['hidden'] = True


    if fldattr.get('user_blurred'):
        kwargs['cellClasses'] = '{cellClasses} gnr_blurred_cell'.format(cellClasses=kwargs.get('cellClasses',''))

    if 'values' in fldattr:
        values = fldattr['values']
        values = getattr(fldobj.table.dbtable, values ,lambda: values)()
        fldattr['values'] = values
        kwargs['values'] = fldattr['values']

    kwargs.update(dictExtract(fldattr,'cell_'))
    kwargs.setdefault('format_pattern',fldattr.get('format'))
    kwargs.setdefault('format',fldattr.get('format'))
    kwargs.update(dictExtract(fldattr,'format_',slice_prefix=False))
    if getattr(fldobj,'sql_formula',None) and fldobj.sql_formula is not True and \
        fldobj.sql_formula.startswith('@') and '.(' in fldobj.sql_formula:
        kwargs['_subtable'] = True
    kwargs['name'] =  fldobj.name_short or fldobj.name_long
    kwargs['dtype'] =  fldobj.dtype
    
    kwargs['dfltwidth'] = '%iem' % int(fldobj.print_width*.6) if fldobj.print_width else None
    for attr in ['caption_field', '_owner_package', 'required_columns']:
        if fldattr.get(attr):
            kwargs[attr] = fldattr[attr]
        
    relfldlst = tableobj.fullRelationPath(field).split('.')
    validations = dictExtract(fldobj.attributes,'validate_',slice_prefix=False)
    if fldattr.get('user_readonly'):
        kwargs.pop('edit',None)
    if validations and kwargs.get('edit'):
        edit = kwargs['edit']
        if edit is not True:
            validations.update(edit)
        kwargs['edit'] = validations
    #if 'values' in fldobj.attributes:
    #    kwargs['values']=fldobj.attributes['values']
    if hasattr(fldobj,'relatedColumnJoiner'):
        columnjoiner = fldobj.relatedColumnJoiner()
        if columnjoiner:
            relatedTable = fldobj.relatedColumn().table
            linktable_attr = relatedTable.attributes
            if linktable_attr.get('checkpref'):
                kwargs['checkpref'] = linktable_attr['checkpref']
                kwargs.update(dictExtract(linktable_attr,'checkpref_'))
            kwargs['related_table'] = relatedTable.fullname
            kwargs['related_table_lookup'] = linktable_attr.get('lookup')
            onerelfld = columnjoiner['one_relation'].split('.')[2]
            isForeignKey = columnjoiner.get('foreignkey')
            storefield = columnjoiner.get('storefield')
            if(onerelfld != relatedTable.pkey):
                kwargs['alternatePkey'] = onerelfld
            if len(relfldlst) == 1:
                caption_field = kwargs.pop('caption_field',None)
                if (caption_field is None) and (isForeignKey or onerelfld == relatedTable.pkey):
                    caption_field =  relatedTable.attributes.get('caption_field')
                if caption_field and not kwargs.get('hidden'):
                    rel_caption_field = '@%s.%s' %(field,caption_field)
                    caption_fieldobj = tableobj.column(rel_caption_field)
                    kwargs['width'] = '%iem' % int(caption_fieldobj.print_width*.6) if caption_fieldobj.print_width else None
                    kwargs['caption_field'] = rel_caption_field
                    caption_field_kwargs = cellFromField(rel_caption_field,tableobj,checkPermissions=checkPermissions)
                    if '_joiner_storename' in caption_field_kwargs:
                        kwargs['_joiner_storename'] = caption_field_kwargs['_joiner_storename']
                        kwargs['_external_fkey'] = caption_field_kwargs['_external_fkey']
                        kwargs['_external_name'] = caption_field_kwargs['_external_name']
                    kwargs['relating_column'] = field
                    kwargs['related_column'] = caption_field
                    kwargs['rowcaption'] = caption_field

    if len(relfldlst) > 1:
        fkey = relfldlst[0][1:]
        kwargs['relating_column'] = fkey
        kwargs['related_column'] = '.'.join(relfldlst[1:])
        fkeycol=tableobj.column(fkey)
        if fkeycol is not None:
            joiner = fkeycol.relatedColumnJoiner()
            ext_fldname = '.'.join(relfldlst[1:])
            if 'storefield' in joiner:
                externalStore(tableobj,field,joiner,fkey,ext_fldname,kwargs)
            elif '_storename' in joiner:
                externalStore(tableobj,field,joiner,fkey,ext_fldname,kwargs)
    
    field_getter = kwargs.get('caption_field') or field
    sqlcolumn = None
    if field_getter.startswith('@'):
        original_field = field_getter
        field_getter = field_getter.replace('.','_').replace('@','_')
        sqlcolumn = '%s AS %s' %(original_field,field_getter)
    else:
        columnobj = tableobj.column(field_getter)
        if columnobj is not None:
            sqlcolumn = '$%s' %field_getter
    kwargs['field_getter'] = field_getter
    kwargs['sqlcolumn'] = sqlcolumn
    return kwargs


def externalStore(tableobj,field,joiner,fkey,ext_fldname,kwargs):
    ext_table = '.'.join(joiner['one_relation'].split('.')[0:2])
    storefield = joiner.get('storefield')
    kwargs['_joiner_storename'] = storefield if storefield else " '%s' " % (joiner.get('_storename') or tableobj.db.rootstore)
    kwargs['_external_fkey'] ='$%s AS %s_fkey' %(fkey,joiner['one_relation'].replace('.','_'))
    if not ext_fldname.startswith('@'):
        ext_fldname = '$%s' %ext_fldname
    kwargs['_external_name'] = '%s:%s AS %s' %(joiner['one_relation'],ext_fldname,field.replace('.','_').replace('@','_'))
