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

caption = 'Stats Grouped'
description = 'Stats Grouped'

class Main(BaseDashboardItem):
    """Choose table and saved stat"""
    item_name = 'Stats Grouped'
    title_template = '$title $whereParsFormatted'
    linked_item = dict(_class='line_chart_white_svg',

                    tip='!!Drag on an empty tile to make a chart',
                    onDrag="""
                    var linkedGrid = genro.getData(dragInfo.sourceNode.attr.workpath+'.currentLinkableGrid');
                    var linkedItem = dragInfo.sourceNode.getRelativeData('.itemIdentifier');
                    dragValues.dashboardItems = {fixedParameters:{'linkedGrid':linkedGrid,title:'Chart #',linkedItem:linkedItem},
                                                    resource:'_groupby_chart',
                                                    caption:_T('Linked chart')};
                    """)

    def content(self,pane,table=None,userobject_id=None,**kwargs):
        self.page.mixinComponent('th/th:TableHandler')
        bc = pane.borderContainer()
        center = bc.contentPane(region='center',_class='hideInnerToolbars')
        frameCode = self.itemIdentifier
        data,metadata = self.page.db.table('adm.userobject').loadUserObject(id=userobject_id)

        frame = center.groupByTableHandler(table=table,frameCode=frameCode,
                                    configurable=False,
                                    struct=data['groupByStruct'],
                                    where='=.query.where',
                                    joinConditions='=.query.joinConditions',
                                    store__fired='^.runStore',
                                    datapath=self.workpath)

        frame.grid.attributes['configurable'] = True #no full configurator but allow selfdragging cols
        frame.stackedView.grid.attributes['configurable'] = True #no full configurator but allow selfdragging cols

        frame.dataController("""
            if(queryPars){
                queryPars.forEach(function(n){
                    var label = n.label.endsWith('*')?n.label.slice(0,n.label.length-1):n.label;
                    where.setItem(n.attr.relpath,conf.getItem('wherepars_'+label));
                });
            }
            FIRE .runStore;
        """,conf='=%s.conf' %self.storepath,
            queryPars='=.query.queryPars',
            where='=.query.where',
            _fired='^%s.runItem' %self.workpath)
        bc.dataController("""var wherePars = new gnr.GnrBag();
                        var subspath = conf_subscriber?conf_subscriber.values().map(v => v.getItem('varpath')):[]
                        conf.forEach(function(n){
                            if(n.label.startsWith('wherepars_') && subspath.indexOf(n.label)<0){
                                wherePars.setItem(n.label.slice(10),n.getValue(),n.attr);
                            }
                        });
                        SET .whereParsFormatted = wherePars.getFormattedValue({joiner:' - '});""",
                    conf='^.conf',conf_subscriber='=.conf_subscriber',_delay=1)

        bc.dataFormula('.currentLinkableGrid','itemIdentifier+(groupMode=="stackedview"?"_stacked_grid":"_grid");',datapath=self.workpath,
                            groupMode='^.groupMode',itemIdentifier=self.itemIdentifier)

        self.queryPars = data['queryPars']
        frame.data('.always',True)
        frame.data('.query.where',data['where'])
        frame.data('.query.queryPars',data['queryPars'])
        frame.data('.query.joinConditions',data['joinConditions'])

        center.dataController("""
            viewMode = viewMode || defaultGroupMode+'_'+defaultOutput;
            genro.nodeById(frameCode).publish('viewMode',viewMode);
        """,viewMode='^.conf.viewMode',
        defaultOutput= data['output'],frameCode=frameCode,
        defaultGroupMode = data['groupMode'],
        _fired='^%s.runItem' %self.workpath)


    def configuration(self,pane,table=None,userobject_id=None,**kwargs):
        bc = pane.borderContainer()
        fb = bc.contentPane(region='top').div(padding='10px').formbuilder()
        fb.filteringSelect(value='^.viewMode',lbl='Mode',
                            values='flatview_grid:Flat grid,stackedview_grid:Stacked view,flatview_tree:Tree,stackedview_tree:Stacked tree')
        center = bc.contentPane(region='center')
        if not self.queryPars:
            return
        fb = center.formbuilder(dbtable=table,
                            fld_validate_onAccept="SET %s.runRequired =true;" %self.workpath)
        for code,pars in self.queryPars.digest('#k,#a'):
            autoTopic = False
            if code.endswith('*'):
                code = code[0:-1]
                autoTopic = True
            field = pars['field']
            rc = self.db.table(table).column(field).relatedColumn()
            wherepath = pars['relpath']
            if pars['op'] == 'equal' and rc is not None:
                wdg = fb.dbSelect(field,value='^.wherepars_%s' %code,lbl=pars['lbl'],
                                    #attr_wdg='dbselect',attr_dbtable=rc.table.fullname,
                                    dbtable=rc.table.fullname,hidden=autoTopic)
            else:
                wdg = fb.textbox(value='^.wherepars_%s' %code,lbl=pars['lbl'],hidden=autoTopic)
            fb.data('.wherepars_%s' %code,pars['dflt'],wdg_tag=wdg.attributes['tag'],
                    wdg_dbtable=wdg.attributes.get('dbtable'),autoTopic=autoTopic)