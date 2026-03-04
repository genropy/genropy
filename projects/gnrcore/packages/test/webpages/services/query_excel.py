# -*- coding: utf-8 -*-
            
from gnr.core.gnrdecorator import public_method

class GnrCustomWebPage(object):
    py_requires='gnrcomponents/externalcall:BaseRpc'

    @public_method
    def ext_query(self, table=None, query_name=None, view_name=None, **kwargs):
        """Set a query named "comuni_regione" on table "comuni", with condition "@provincia.$regione=:reg"
        Then import query in Excel from SampleWebQueryPROV.iqy (see test resources). 
        Insert Regione Code as parameter."""
        #query_name "comuni_regione"
        selection,resultattr = self.app.getSelection(table=table, savedQuery=query_name, 
                                    savedView=view_name,selectionOutput=False,addPkeyColumn=False, **kwargs)
        result = ['<table>']
        result.append('<tr>')
        result.append(''.join(['<th>{colname}</th>'.format(colname=colname) for colname in selection.colHeaders]))
        result.append('</tr>')
        for r in selection.output('generator'):
            result.append('<tr>')
            result.append(''.join(['<td>{}</td>'.format(c[1]) for c in r]))
            result.append('</tr>')
        result.append('</table>')
        return ''.join(result)
