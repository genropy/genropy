# -*- coding: utf-8 -*-
#--------------------------------------------------------------------------
# package       : GenroPy core - see LICENSE for details
# module gnrlis : gnr list implementation
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

try:
    import openpyxl  # noqa: F401
    from gnr.core.gnrxls import XlsxWriter as ExcelWriter
except:
    from gnr.core.gnrxls import XlsWriter as ExcelWriter

def getWriter(mode):
    writers = {
        'csv':CsvWriter,
        'html':HtmlTableWriter,
        'json':JsonWriter,
        'xls':ExcelWriter
    }
    return writers[mode]


class BaseWriter(object):
    content_type = 'text/plain'
    def __init__(self, columns=None, coltypes=None, headers=None, filepath=None,locale=None, rowseparator=None,colseparator=None,**kwargs):
        self.headers = headers or []
        self.columns = columns
        self.coltypes = coltypes
        self.filepath = filepath
        self.locale = locale
        self.result = []
        self.rowseparator = rowseparator
        self.colseparator = colseparator
        from gnr.core.gnrstring import toText
        self.toText = toText

    def cleanCol(self, txt, dtype):
        if self.rowseparator:
            txt = txt.replace(self.rowseparator,' ')
        if self.colseparator:
            txt = txt.replace(self.colseparator,' ')
        txt = txt.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ').replace('"', "'")
        if txt:
            if txt[0] in ('+', '=', '-'):
                txt = ' %s' % txt
            elif txt[0].isdigit() and (dtype in ('T', 'A', '', None)):
                txt = '%s' % txt # how to escape numbers in text columns?
        return txt

    def writeHeaders(self, separator='\t',**kwargs):
        pass

    def writeRow(self, row, separator='\t',**kwargs):
        pass

    def join(self,data):
        return self.rowseparator.join(list(data))


    def workbookSave(self):
        if not self.filepath:
            return '\n'.join(self.result)
        if hasattr(self.filepath, 'open'):
            csv_open = self.filepath.open
        else:
            csv_open = lambda **kw: open(self.filepath,**kw)
        with csv_open(mode='wb') as f:
            separator = self.rowseparator or '\n'
            result = separator.join(self.result)
            f.write(result.encode('utf-8'))
    
    def composeAll(self,data=None,filepath=None, **kwargs):
        for export_data in data:
            self.write(export_data)
    
    def compose(self,data):
        raise NotImplementedError
    
    def setStructInfo(self,struct,obj=None):
        obj = obj or self
        for k in ('columns','headers','groups','coltypes','formats'):
            setattr(obj,k,struct.get(k))


class CsvWriter(BaseWriter):
    """docstring for CsVWriter"""
    extension = 'csv'

    def __init__(self, columns=None, coltypes=None, headers=None, filepath=None, locale=None,rowseparator=None,colseparator=None, **kwargs):
        rowseparator = rowseparator or '\n'
        super().__init__(columns=columns, coltypes=coltypes, headers=headers, filepath=filepath, locale=locale,rowseparator=rowseparator,colseparator=colseparator, **kwargs)

    def writeHeaders(self, separator=None,**kwargs):
        self.result.append(self.composeHeader(separator=separator,**kwargs))

    def writeRow(self, row, separator=None,**kwargs):
        self.result.append(self.composeRow(row,separator=separator,**kwargs))


    def composeHeader(self, separator=None,**kwargs):
        separator = separator or self.colseparator or '\t'
        return separator.join(self.headers)

    def composeRow(self, row, separator=None,**kwargs):
        separator = separator or self.colseparator or '\t'
        return separator.join([self.cleanCol(self.toText(row.get(col),locale=self.locale), self.coltypes.get(col,'T')) for col in self.columns])

    def composeAll(self,data=None,**kwargs):
        firstExport = True
        extra_headers = []
        extra_columns = []
        if not (isinstance(data,list) and len(data)==1):
            extra_headers =  ['Identifier','Caption']
            extra_columns = ['_export_identifier','_export_caption']
        for export_data in data:
            if firstExport:
                struct = export_data['struct']
                self.headers = extra_headers + struct['headers']
                self.columns =  extra_columns + struct['columns']
                self.coltypes = struct['coltypes']
                firstExport = False
                yield self.composeHeader()
            for r in export_data['rows']:
                r['_export_identifier'] = export_data.get('identifier')
                r['_export_caption'] = export_data.get('name')
                yield self.composeRow(r)




class HtmlTableWriter(BaseWriter):
    content_type = 'text/html'
    extension = 'html'

    def __init__(self, columns=None, coltypes=None, headers=None, filepath=None, locale=None,rowseparator=None, **kwargs):
        rowseparator = rowseparator or '<br/>'
        super().__init__(columns=columns, coltypes=coltypes, headers=headers, filepath=filepath, locale=locale,rowseparator=rowseparator, **kwargs)
        self.rows = []

    def writeHeaders(self, separator='',**kwargs):
        self.result.append(self.composeHeaders(separator=separator))

    def writeRow(self, row, separator='',**kwargs):
        self.rows.append(self.composeRow(row,separator=separator))
    
    def composeHeaders(self,separator='',**kwargs):
        return f'<thead>{separator.join(["<th>%s</th>" %h for h in self.headers])}</thead>'

    def composeRow(self,row, separator='',**kwargs):
        return f"<tr>{separator.join(['<td>%s</td>' %self.cleanCol(self.toText(row.get(col),locale=self.locale), self.coltypes[col]) for col in self.columns])}</tr>"


    def workbookSave(self):
        self.result.append('<tbody>%s</tbody>' %''.join(self.rows))
        result = '<table>%s</table>' %''.join(self.result)
        if not self.filepath:
            return result
        if hasattr(self.filepath, 'open'):
            csv_open = self.filepath.open
        else:
            csv_open = lambda **kw: open(self.filepath,**kw)
        with csv_open(mode='wb') as f:
            f.write(result.encode('utf-8'))

    def composeAll(self,data=None,**kwargs):
        for export_data in data:
            yield self.compose(export_data)
    
    def compose(self,data):
        self.setStructInfo(data['struct'])
        result = []
        name = data['name']
        result.append(f'<table class="gnrexport_tbl"><caption>{name}</captipn>')
        result.append(self.composeHeaders())
        result.append('<tbody>')
        for row in data['rows']:
            result.append(self.composeRow(row))
        result.append('</tbody>')
        result.append('</table>')
        return ''.join(result)

    def save(self,storageNode=None):
        with storageNode.open('wb') as f:
            f.write('<br/>'.join(self.result))




class JsonWriter(BaseWriter):
    extension = 'json'

    def writeRow(self, row, **kwargs):
        self.result.append({col:self.cleanCol(self.toText(row.get(col),locale=self.locale), self.coltypes[col]) for col in self.columns })
    
    def workbookSave(self):
        if not self.filepath:
            return ''.join(self.result)
        if hasattr(self.filepath, 'open'):
            csv_open = self.filepath.open
        else:
            csv_open = lambda **kw: open(self.filepath,**kw)
        with csv_open(mode='wb') as f:
            result = ''.join(self.result)
            f.write(result.encode('utf-8'))
