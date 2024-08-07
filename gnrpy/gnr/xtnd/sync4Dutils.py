# -*- coding: utf-8 -*-
# Genro  
# Copyright (c) 2004 Softwell sas - Milano see LICENSE for details
# Author Giovanni Porcari, Francesco Cavazzana, Saverio Porcari, Francesco Porcari
import os.path
from gnr.core.gnrbag import Bag


class Utils4D(object):
    def __init__(self,emptyAsNone=None):
        self.emptyAsNone = emptyAsNone

    def bag4dTableToListDict(self, b):
        result = []
        if 'New' in b:
            b = b['New']
        if 'new' in b:
            b = b['new']
        if b:
            keys = list(b.keys())
            values = [k or [] for k in list(b.values())]
            n = len(values[0])
            for v in values:
                if len(v) < n:
                    v.extend([None] * (n - len(v)))
            result = [dict([(k.lower(), self.checkValue(values[i][x])) for i, k in enumerate(keys)]) for x in range(n)]
        return result

    def listDictTobag4dTable(self, listdict):
        result = Bag()
        for k in list(listdict[0].keys()):
            result[k] = [d.get(k) for d in listdict]
        return result

    def checkValue(self,v):
        if isinstance(v,str):
            v = v.strip()
            if self.emptyAsNone and v == '':
                v = None
        return v

class Pkg4D(object):
    def _structFix4D(self, struct, path):
        cnv_file = '%s_conv%s' % os.path.splitext(path)
        if os.path.isfile(cnv_file):
            return cnv_file
        cls = struct.__class__
        b = Bag()
        b.fromXml(path, bagcls=cls, empty=cls)

        convdict = {'ci_relation': None,
                    'o_name': None,
                    'o_name_short': None,
                    'o_name_full': None,
                    'o_name_long': None,
                    'many_name_short': None,
                    'many_name_full': None,
                    'many_name_long': None,
                    'eager_relation': None,
                    'len_max': None,
                    'len_min': None,
                    'len_show': None,
                    'relation': None,
                    'comment': None
        }
        #relate_attrs = set(('ci_relation', 'o_name', 'o_name_short', 'o_name_full', 'o_name_long',
        #                    'many_name_short','many_name_full','many_name_long','eager_relation'))

        for pkg in b['packages']:
            for tbl in pkg.value['tables']:
                for col in tbl.value['columns']:
                    newattrs = {}
                    for k, v in list(col.attr.items()):
                        if v is not None:
                            lbl = convdict.get(k, k)
                            if lbl:
                                newattrs[lbl] = v
                    name_long = newattrs.get('name_long')
                    if name_long:
                        if name_long[0] == name_long[0].lower():
                            newattrs['group'] = '_'
                        if name_long.endswith('_I'):
                            name_long = name_long[:-2]
                        elif not 'indexed' in newattrs:
                            newattrs['group'] = '*'
                        if len(name_long) > 2 and name_long[2] == '_':
                            name_long = name_long[3:]
                        newattrs['name_long'] = name_long.replace('_', ' ')

                    if 'len_max' in col.attr:
                        newattrs['size'] = '%s:%s' % (col.attr.get('len_min', '0'), col.attr['len_max'])
                    if 'relation' in col.attr:
                        mode = None
                        if col.attr.get('ci_relation'):
                            mode = 'insensitive'
                        col.value = Bag()
                        col.value.setItem('relation', None, related_column=col.attr['relation'], mode=mode)
                    col.attr = newattrs
        b.toXml(cnv_file)
        return cnv_file

def gnr4dNetBag (host4D, method, params=None):
    """Call a 4D method via 4D WebService Server and GnrNetBag
    @param host4D: host (and port) of the 4D webserver
    @param method: name of the method to invoke on 4D in the form 4dMethod.$1:$2
    @param params: a Bag containing all needed params: 4D receive it as $3 (string: name of a GnrViVa BLOB)"""
    from SOAPpy import SOAPProxy

    server = SOAPProxy("http://" + host4D + "/4DSOAP",
                       namespace="http://www.4d.com/namespace/default",
                       soapaction="A_WebService#GNT_NetBags_Server",
                       encoding="iso-8859-1",
                       http_proxy="")

    params = params or Bag()
    params['NetBag.Method'] = method
    params['NetBag.Compression'] = 'N'
    params['NetBag.Session'] = ''
    params['NetBag.UserID'] = ''

    #xml = params.toXml(encoding='iso-8859-1')
    xml = str(params.toXml(mode4d=True, encoding='iso-8859-1'), encoding='iso-8859-1')
    #print xml
    result = server.GNT_NetBags_Server(FourD_Arg1=xml)
    return Bag(result)

def gnr4dNetBag_ (host4D, method, params=None):
    """Call a 4D method via 4D WebService Server and GnrNetBag
    @param host4D: host (and port) of the 4D webserver
    @param method: name of the method to invoke on 4D in the form 4dMethod.$1:$2
    @param params: a Bag containing all needed params: 4D receive it as $3 (string: name of a GnrViVa BLOB)"""
    from suds.client import Client

    server = Client("http://" + host4D + "/4DWSDL/")#, namespace="http://www.4d.com/namespace/default")#,
                       #soapaction="A_WebService#GNT_NetBags_Server",
                       #encoding="iso-8859-1",
                       #http_proxy="")

    params = params or Bag()
    params['NetBag.Method'] = method
    params['NetBag.Compression'] = 'N'
    params['NetBag.Session'] = ''
    params['NetBag.UserID'] = ''

    #xml = params.toXml(encoding='iso-8859-1')
    xml = str(params.toXml(encoding='iso-8859-1'), encoding='iso-8859-1')
    result = server.service.GNT_NetBags_Server(FourD_Arg1=xml)

    return Bag(result)

if __name__ == '__main__':
    print(gnr4dNetBag('192.168.1.176:8080', 'ATestPy.Ping:pippo'))