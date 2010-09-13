# -*- coding: UTF-8 -*-
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


"""
Some useful operations on lists.
"""

def findByAttr(l,**kwargs):
    """
    Find elements in list "l" having attributes with names and values as kwargs items
    """
    result = list(l)
    for k,v in kwargs.items():
        result = [x for x in result if getattr(x,k,None) == v]
    return result

def sortByItem(l, *args, **kwargs):
    """Sort the list "l", filled of objects with dict interface by items with key in *args.
       @param *args: a list of keys to sort for. Each key can be reverse sorted by adding ':d' to the key.
       @param hkeys: if True and a key contains '.' it is interpreted as a hierarchical path and sub dict are looked for
       """
    def safeCmp(a,b):
        if a is None :
            if b is None:
                return 0
            return -1
        elif b is None:
            return 1
        else:
            return cmp(a,b)

    def hGetItem(obj,attr):
        if obj is None: return None
        if not '.' in attr:
            return obj.get(attr,None)
        else:
            curr,next = attr.split('.',1)
            return hGetAttr(obj.get(curr,None),next)
        
    criteria = []
    rev = False
    for crit in list(args):
        caseInsensitive=False
        if ':' in crit: 
            crit, direction = crit.split(':',1)
            if direction.endswith('*'):
                direction=direction[0:-1]
                caseInsensitive=True
            if direction.lower() in[ 'd','desc','descending']:
                rev=not rev
        criteria=[(crit, rev,caseInsensitive)]+criteria
    hkeys = kwargs.get('hkeys', False)
    
    for crit,rev,caseInsensitive in criteria:
        if caseInsensitive:
            if '.' in crit and hkeys:
                l.sort(lambda a,b: safeCmp((hGetItem(a,crit) or '').lower(),(hGetItem(b,crit) or '').lower()))
            else:
                l.sort(lambda a,b: safeCmp((a.get(crit,None) or '').lower(),(b.get(crit,None) or '').lower()))
        else:
            if '.' in crit and hkeys:
                l.sort(lambda a,b: safeCmp(hGetItem(a,crit),hGetItem(b,crit)))
            else:
                l.sort(lambda a,b: safeCmp(a.get(crit,None),b.get(crit,None)))
        if(rev):
            l.reverse()
    return l

def sortByAttr(l,*args):
    # da verificare
    def hGetAttr(obj,attr):
        if obj is None: return None
        if not '.' in attr:
            return getattr(obj,attr,None)
        else:
            curr,next = attr.split('.',1)
            return hGetAttr(getattr(obj,curr,None),next)
    criteria = list(args)
    criteria.reverse()
    for crit in criteria:
        rev = None
        if ':' in crit: crit,rev = crit.split(':',1)
        if '.' in crit:
            l.sort(lambda a,b: cmp(hGetAttr(a,crit),hGetAttr(b,crit)))
        else:
            l.sort(lambda a,b: cmp(getattr(a,crit,None),getattr(b,crit,None)))
        if rev:
            l.reverse()
    return l
    
def merge(*args):
    result = list(args[0])
    for l in args[1:]:
        for el in l:
            if not el in result:
                result.append(el)
    return result
    
def readTab(doc):
    """This reads a tab delimited file, the previous function readCSV was misnamed but must be left for legacy"""
    if isinstance(doc, basestring):
        f = open(doc)
    else:
        f = doc


    txt = f.read()
    txt = txt.replace('\r\n', '\n')
    txt = txt.replace('\r', '\n')
    lines = txt.split('\n')
    txt = None
    u = [line.split('\t') for line in lines]
    headers = u[0]
    rows = u[1:]

    index = dict([(k,i) for i,k in enumerate(headers)])

    ncols = len(headers)
    for row in rows:
        if len(row) == ncols: # it works only for rows with the same length of header
            yield GnrNamedList(index, row)

    if isinstance(doc, basestring):
        f.close()  

def readCSV_new(doc):
    """This reads a CSV file - done by Jeff"""
    if isinstance(doc, basestring):
        f = open(doc)
    else:
        f = doc

    txt = f.read()
    txt = txt.replace('\r\n', '\n')
    txt = txt.replace('\r', '\n')
    txt = txt.replace('\",\"', '\t')
    txt = txt.replace('\"', '')
    txt = txt.replace(',', '\t')
    lines = txt.split('\n')
    txt = None
    u = [line.split('\t') for line in lines]
    headers = u[0]
    rows = u[1:]

    index = dict([(k,i) for i,k in enumerate(headers)])

    ncols = len(headers)
    for row in rows:
        if len(row) == ncols: # it works only for rows with the same length of header
            yield GnrNamedList(index, row)

    if isinstance(doc, basestring):
        f.close()

def readCSV(doc):
    if isinstance(doc, basestring):
        f = open(doc)
    else:
        f = doc
    
    txt = f.read()
    txt = txt.replace('\r\n', '\n')
    txt = txt.replace('\r', '\n')
    lines = txt.split('\n')
    txt = None
    u = [line.split('\t') for line in lines]
    headers = u[0]
    rows = u[1:]
    index = dict([(k,i) for i,k in enumerate(headers)])
    ncols = len(headers)
    for row in rows:
        if len(row) == ncols: # it works only for rows with the same length of header
            yield GnrNamedList(index, row)
            
    if isinstance(doc, basestring):
        f.close()


def readXLS(doc):
    import xlrd
    if isinstance(doc, basestring):
        filename = doc
        file_contents = None
    else:
        filename = None
        file_contents = doc.read()

    book = xlrd.open_workbook(filename=filename, file_contents=file_contents)
    sheet=book.sheet_by_index(0)
    
    headers = [sheet.cell_value(0, c) for c in range(sheet.ncols)]
    headers = [h for h in headers if h]
    
    index = dict([(k,i) for i,k in enumerate(headers)])
    
    ncols = len(headers)
    for r in range(1, sheet.nrows):
        row = [sheet.cell_value(r, c) for c in range(ncols)]
        yield GnrNamedList(index, row)
            
    
        
        
class GnrNamedList(list):
    """A row object that allow by-column-name access to data, the capacity to add columns and alter data."""
    def __init__(self, index, values=None):
        self._index = index
        if values is None:
            self[:] = [None] * len(index)
        else:
            self[:] = values
            
    def __getitem__(self, x):
        if type(x) != int:
            x = self._index[x]
        try:
            return list.__getitem__(self, x)
        except:
            if x > len(self._index):
                raise
    def __contains__(self, what):
        return what in self._index
                
    def pop(self, x):
        if type(x) != int:
            x = self._index[x]
        try:
            return list.pop(self, x)
        except:
            if x > len(self._index):
                raise
    
    #def __getattribute__(self, x):
    #    if type(x) != int:
    #        x = self._index[x]
    #    try:
    #        return list.__getattribute__(self, x)
    #    except:
    #        if x > len(self._index):
    #            raise
                
    #def __delattr__(self,x):
    #    if type(x) != int:
    #        x = self._index[x]
    #    try:
    #        return list.__delattr__(self, x)
    #    except:
    #        if x > len(self._index):
    #            raise
            
    def __setitem__(self, x, v):
        if type(x) != int:
            n = self._index.get(x)
            if n is None:
                n = len(self._index)
                self._index[x] = n
            x = n
        try:
            list.__setitem__(self, x, v)
        except:
            n = len(self._index)
            if x > n:
                raise
            else:
                self.extend([None] * (n-len(self)))
                list.__setitem__(self, x, v)
                
    def __str__(self):
        return '[%s]'%','.join(['%s=%s'%(k,v) for k,v in self.items()])
    
    def __repr__(self):
        return '[%s]'%','.join(['%s=%s'%(k,v) for k,v in self.items()])
                
    def items(self):
        items = self._index.items()
        result = [None] * len(items)
        for k,v in items:
            result[v] = (k, self[v])
        return result
    
    def keys(self):
        items = self._index.items()
        result = [None] * len(items)
        for k,v in items:
            result[v] = k
        return result

    def values(self):
        return tuple(self[:] + [None] * (len(self._index)-len(self)))

    def has_key(self, x):
        return self._index.has_key(x)

    def get(self, x, default=None):
        try:
            return self[x]
        except:
            return default
        
    def update(self, d):
        for k,v in d.items():
            self[k] = v
        
    def iteritems(self):
        items = self._index.items()
        result = [None] * len(items)
        for k,v in items:
            yield (k, self[v])
            
    def extractItems(self, columns):
        if columns:
            return [(k, self[k]) for k in columns]
        else:
            return self.items()
        
    def extractValues(self, columns):
        if columns:
            return [self[k] for k in columns]
        else:
            return self.values()
        


    