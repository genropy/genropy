# -*- coding: UTF-8 -*-
#--------------------------------------------------------------------------
# Copyright (c) : 2004 - 2007 Softwell sas - Milano 
# Written by    : Giovanni Porcari, Michele Bertoldi
#                 Saverio Porcari, Francesco Porcari
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


from gnrpkg.biz.dashboard import BaseDashboardItem
from gnr.core.gnrbag import Bag


caption = 'Table view'
description = 'Table view'

class Main(BaseDashboardItem):
    title_template = '$title $whereParsFormatted'

    def content(self,pane,table=None,userobject_id=None,**kwargs):
        self.page.mixinComponent('th/th:TableHandler')
        bc = pane.borderContainer(datapath=self.workpath)
        center = bc.contentPane(region='center')
        
        selectionViewer = self._selectionViewer(center,table=table,
                                            userobject_id=userobject_id,
                                            datapath='.viewer')
        self.queryPars = selectionViewer.queryPars
        self.content_handleQueryPars(selectionViewer)
        pane.dataFormula('.whereParsFormatted',"wherePars?wherePars.getFormattedValue({joiner:' - '}):'-'",
                    wherePars='^.conf.wherePars')


    def configuration(self,pane,table=None,queryName=None,**kwargs):
        if not self.queryPars:
            return
        self.configuration_handleQueryPars(pane,table)

    def _selectionViewer(self,pane,table=None,userobject_id=None,fired=None,**kwargs):
        tblobj = self.page.db.table(table)
        userobject_tbl = self.page.db.table('adm.userobject')
        data,metadata = userobject_tbl.loadUserObject(id=userobject_id,tbl=table)
        customOrderBy = None
        limit = None
        queryPars = None
        limit = data['limit']
        viewName = data['currViewPath']
        customOrderBy = data['customOrderBy']
        joinConditions = data['joinConditions']
        queryPars = data.pop('queryPars')
        extraPars = data.pop('extraPars')
        where = data['where']
        struct = data['struct']
        frame = pane.frameGrid(struct=struct,_newGrid=True,frameCode=self.itemIdentifier,**kwargs)
        frame.data('.query.limit',limit)
        frame.data('.query.where',where)
        frame.data('.query.extraPars',extraPars)
        frame.data('.query.queryPars',queryPars)
        frame.data('.query.customOrderBy',customOrderBy)
        frame.data('.query.joinConditions',joinConditions)
        frame.top.slotBar('*,vtitle,*',vtitle=metadata['description'])
        frame.queryPars = queryPars
        frame.grid.selectionStore(table=table,childname='store',where='=.query.where',
                                customOrderBy='=.query.customOrderBy',
                                joinConditions='=.query.joinConditions',
                                limit='=.query.limit',
                                _fired='^.run')
        return frame

    
    def getDashboardItemInfo(self,table=None,userObjectData=None,**kwargs):
        result = []
        where = userObjectData['where']
        struct = userObjectData['struct']
        if struct:
            z = [self.localize(n.attr.get('name')) for n in struct['view_0.rows_0'].nodes if not n.attr.get('hidden')]
            result.append('<div class="di_pr_subcaption" >Fields</div><div class="di_content">%s</div>' %','.join(z))
        if where:
            result.append('<div class="di_pr_subcaption">Where</div><div class="di_content">%s</div>' %self.db.whereTranslator.toHtml(self.db.table(table),where))
        configurations = []
        queryPars = userObjectData['queryPars']
        if queryPars:
            for code,pars in queryPars.digest('#k,#a'):
                autoTopic = False
                if not code.endswith('*'):
                    configurations.append(code)
        if configurations:
            result.append('<div class="di_pr_subcaption">Config</div><div class="di_content">%s</div>' %'<br/>'.join(configurations))


        return ''.join(result)
    
    def itemActionsSlot(self,pane):
        pane.lightbutton(_class='excel_white_svg',
                        action="""
                        var opt = objectExtract(_kwargs,'opt_*');
                        var kw = {command:'export',opt:opt};
                        var gridId = 'temIdentifier+'_grid';
                        genro.nodeById(gridId).publish('serverAction',kw)""",
                        groupMode='=.groupMode' ,datapath=self.workpath,
                        itemIdentifier=self.itemIdentifier,height='16px',width='16px',
                        opt_export_mode='xls',
                        opt_downloadAs='=.current_title?=#v?flattenString(#v,[".",":","/",";"," "]).toLowerCase():""',
                        opt_rawData=True, 
                        opt_localized_data=True,
                        ask=dict(title='Export selection',skipOn='Shift',
                                fields=[dict(name='opt_downloadAs',lbl='Download as'),
                                        dict(name='opt_export_mode',wdg='filteringSelect',values='xls:Excel,csv:CSV',lbl='Mode'),
                                        dict(name='opt_allRows',label='All rows',wdg='checkbox'),
                                        dict(name='opt_localized_data',wdg='checkbox',label='Localized data')]),
                        cursor='pointer')