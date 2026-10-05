# -*- coding: utf-8 -*-

# th_user.py
# Created by Saverio Porcari on 2011-03-13.
# Copyright (c) 2011 Softwell. All rights reserved.

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method
from gnr.core.gnrbag import Bag
class View(BaseComponent):
    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('name', name='!!Name', width='20em')
        r.fieldcell('username', name='!!Username', width='10em')
        r.fieldcell('version', name='!!Version', width='20em')        
        
    def th_order(self):
        return 'name'
        
    def th_query(self):
        return dict(column='name',op='contains', val='')

class Form(BaseComponent):
    css_requires = 'letterhead'
    py_requires = "gnrcomponents/attachmanager/attachmanager:AttachManager"
    def th_form(self, form):
        bc = form.center.borderContainer()
        bc.css('.printRegion', 'margin:.5mm;border:.3mm dotted silver;cursor:pointer;')
        bc.data('zoomFactor', .5)
        #self.editorDialog(bc)
        self.htmltemplate_controllers(bc)
        self.htmltemplate_mainInfo(bc.borderContainer(region='left', width='60em', splitter=True,datapath='.record'))
        bc.borderContainer(region='center', overflow='auto', datapath='#FORM._temp.data').remote(self.htmltemplate_printLayout,
                                                                                           design='^#FORM.record.data.main.design')


    @public_method
    def htmltemplate_printLayout(self, parentBc, design=None, **kwargs):
        page = parentBc.borderContainer(region='center',
                                        height='^.main.page.height',
                                        width='^.main.page.width',
                                        border='1px solid gray', style="""
                                                                    background-color:white;
                                                                    -moz-box-shadow:8px 8px 15px gray;
                                                                    -webkit-box-shadow:8px 8px 15px gray;
                                                                    """,
                                        zoom='^zoomFactor', margin='10px')
        layers = page.contentPane(region='center',overflow='hidden')
        layers.div('^#FORM.backgroundLetterhead',position='absolute',top=0,left=0,right=0,bottom=0,
                    _class='backgroundLetterhead',visible='^#FORM.showBackground')
        layer_1 = layers.div(position='absolute',top=0,left=0,right=0,bottom=0,z_index=1)
        layer_1.dataController('SET #FORM.currentEditedArea = "dummy";',_fired='^#FORM.controller.loaded')
        bc = layer_1.borderContainer(position='absolute',
                                  top='^.main.page.top',
                                  bottom='^.main.page.bottom',
                                  left='^.main.page.left',
                                  right='^.main.page.right',
                                  connect_ondblclick="""
                                    var that = this;
                                    var clickedNode = dijit.getEnclosingWidget($1.target).sourceNode;
                                    
                                    if(clickedNode){
                                        let abspath = clickedNode.absDatapath();
                                        this.getDomNode().parentElement.setAttribute('class','selected_'+abspath.split('.').slice(-3).join('_'))
                                        SET #FORM.currentEditedArea = 'dummy';
                                        setTimeout(function(){
                                            that.setRelativeData('#FORM.currentEditedArea',abspath);
                                        },1);
                                    }
                                """,
                                  #_class='hideSplitter',
                                  regions='^#FORM._temp.data.layout.regions',
                                  design=design
                                  )
        regions = dict(headline=('top', 'bottom', 'center'), sidebar=('left', 'right', 'center'))
        for region in regions[design]:
            self._htmltemplate_subRegions(bc, region=region, design=design)


    def _htmltemplate_subRegions(self, parentBc, region=None, design=None):
        subregions = dict(sidebar=('top', 'bottom', 'center'), headline=('left', 'right', 'center'))
        bc = parentBc.borderContainer(region=region, splitter=(region != 'center'),
                                      _class='hideSplitter', datapath='.layout.%s' % region,
                                      regions='^.regions')
        for subregion in subregions[design]:
            bc.contentPane(region=subregion, _class='printRegion {region}_{subregion}'.format(region=region,subregion=subregion), splitter=(subregion != 'center'),
                           datapath='#FORM.record.data.layout.%s.%s' % (region, subregion)).div(innerHTML='^.html')

    def htmltemplate_controllers(self, pane):
        for part in ('height', 'width', 'top', 'bottom', 'left', 'right'):
            pane.dataFormula("#FORM._temp.data.main.page.%s" % part, "part+'mm';", part='^#FORM.record.data.main.page.%s' % part)
        pane.dataFormula("#FORM._temp.data.main.design", "design", design="^#FORM.record.data.main.design")
        pane.dataFormula('#FORM.record.center_height',"Math.floor(page_height-page_margin_top-page_margin_bottom-header_height-footer_height)",
                            page_height='^.main.page.height',
                            page_margin_top='^.main.page.top',
                            page_margin_bottom='^.main.page.bottom',
                            header_height='^.layout.top?height',
                            footer_height='^.layout.bottom?height',
                            datapath='#FORM.record.data')

        pane.dataFormula('#FORM.record.center_width',"Math.floor(page_width-page_margin_left-page_margin_right-side_left-side_right)",
                            page_width='^.main.page.width',
                            page_margin_left='^.main.page.left',
                            page_margin_right='^.main.page.right',
                            side_left='^.layout.left?width',
                            side_right='^.layout.right?width',
                            datapath='#FORM.record.data')

    def htmltemplate_mainInfo(self, bc):
        self.htmltemplate_form(bc.contentPane(region='top', padding='2px'))
        center = bc.roundedGroupFrame(region='center',datapath='^#FORM.currentEditedArea',overflow='hidden')
        center.center.contentPane(overflow='hidden').joditEditor(value='^.html',nodeId='htmlEditor',
                    disabled='^#FORM.currentEditedArea?=isNullOrBlank(#v)||#v=="dummy"',toolbar='standard',
                    height='100%')
        bottom = center.bottom
        bar = bottom.slotBar('picker_flib,5,atcPalette,*,editedArea,10,showBackground,5,zoomfactor,5',
                             _class='pbl_roundedGroupBottom')
        bar.dataFormula('#FORM.currentEditedAreaCaption',
                        "area && area!='dummy' ? area.split('.').slice(-2).join(' · ') : ''",
                        area='^#FORM.currentEditedArea')
        bar.editedArea.div('^#FORM.currentEditedAreaCaption', color='#888', font_size='.9em')
        bar.showBackground.div(margin_top='1px').checkbox(value='^#FORM.showBackground',label='Background letterheads',default=True)
        if 'flib' in self.db.packages:
            self.mixinComponent('flib:FlibPicker')
            bar.picker_flib.flibPicker(dockButton=dict(label='Files'),viewResource=':ImagesView')
        else:
            bar.picker_flib.div()
        bar.atcPalette.palettePane(paletteCode='atcPalette',title='Attachments',dockButton=dict(label='Attachments'),
                                height='800px',width='500px').attachmentGallery()
        bar.zoomfactor.horizontalSlider(value='^zoomFactor', minimum=0, maximum=1,
                                intermediateChanges=True, width='15em', float='right')

    def htmltemplate_form(self, pane):
        box = pane.gridbox(columns='4fr 3fr', gap='4px')
        self.htmltemplate_tplInfo(self._htmltemplate_group(box, '!!Info')[1])
        self.htmltemplate_basePageParams(self._htmltemplate_group(box, '!!Page sizing (mm)',
                                                                  datapath='.data.main.page')[1])
        self.htmltemplate_layout(*self._htmltemplate_group(box, '!!Layout (mm)', colspan=2))

    def _htmltemplate_group(self, box, title, **kwargs):
        # roundedGroup is absolutely positioned and would collapse the auto-sized top region
        group = box.div(_class='pbl_roundedGroup', **kwargs)
        header = group.div(_class='pbl_roundedGroupLabel').div(display='flex', align_items='center', gap='12px')
        header.div(title)
        return header, group.div(_class='pbl_roundedGroupContent')

    def htmltemplate_tplInfo(self, pane):
        fl = pane.formlet(cols=2)
        fl.field('name', colspan=2)
        fl.field('based_on', hasDownArrow=True, lbl='!!Based on', condition='$id!=:curr_id',
                 condition_curr_id='=#FORM.record.id')
        fl.field('next_letterhead_id', hasDownArrow=True, lbl='!!Follow on')
        fl.field('type_code', hasDownArrow=True, lbl='!!Type')
        fl.field('version', lbl='!!V.')
        pane.dataRpc('#FORM.backgroundLetterhead',self.loadBasedOn,letterhead_id='^.based_on',_if='letterhead_id',_else='return "";')

    @public_method
    def loadBasedOn(self,letterhead_id=None,**kwargs):
        letterheadtbl = self.db.table('adm.htmltemplate')
        base = letterheadtbl.getHtmlBuilder(letterhead_pkeys=letterhead_id)
        base.finalize(base.body)
        basehtml = base.root.getItem('#0.#1').toXml(omitRoot=True,autocreate=True,forcedTagAttr='tag',docHeader=' ',
                                        addBagTypeAttr=False, typeattrs=False, 
                                        self_closed_tags=['meta', 'br', 'img'])
        return basehtml.replace('letterhead_page','')

    def htmltemplate_basePageParams(self, pane):
        fl = pane.formlet(cols=2)
        for part in ('height', 'width', 'top', 'bottom', 'left', 'right'):
            fl.numberTextBox(value='^.%s' % part, lbl='!!%s' % part.title())

    def htmltemplate_layout(self, header, pane):
        header.div(font_weight='normal').multiButton(value='^.data.main.design',
                                                     values='headline:Headline,sidebar:Sidebar')
        layout = pane.div(datapath='.data.layout')
        for design, bands, band_size, sides, side_size in (('headline', ('top', 'bottom'), 'height', ('left', 'right'), 'width'),
                                                           ('sidebar', ('left', 'right'), 'width', ('top', 'bottom'), 'height')):
            fl = layout.formlet(cols=5, hidden='^#FORM.record.data.main.design?=#v!="%s"' % design)
            for row, band in enumerate(bands):
                self._htmltemplate_regionSize(layout, fl, band, band_size, temp_path='regions.%s' % band,
                                              lbl='!!%s %s' % (band.title(), band_size))
                for side in sides:
                    self._htmltemplate_regionSize(layout, fl, '%s.%s' % (band, side), side_size,
                                                  temp_path='%s.regions.%s' % (band, side),
                                                  lbl='!!%s %s' % (band.title(), side))
                if row == 0:
                    for side in sides:
                        self._htmltemplate_regionSize(layout, fl, 'center.%s' % side, side_size,
                                                      temp_path='center.regions.%s' % side,
                                                      lbl='!!Center %s' % side)
            fl.numberTextBox(value='^#FORM.record.center_height', lbl='!!Center height', readOnly=True)
            fl.numberTextBox(value='^#FORM.record.center_width', lbl='!!Center width', readOnly=True)

    def _htmltemplate_regionSize(self, layout, fl, path, size, temp_path=None, lbl=None):
        data_path = '%s?%s' % (path, size)
        fl.numberTextBox(value='^.%s' % data_path, lbl=lbl)
        layout.dataController("""this.setRelativeData('#FORM._temp.data.layout.%s',
                                                parseInt((val||0)*3.779527559)+'px',
                                                {show:val!=0});""" % temp_path,
                              val='^.%s' % data_path)
        layout.dataController(
                "if(_triggerpars.kw.reason!=true){SET .%s = dojo.number.round(parseFloat(val.slice(0,-2))/3.779527559,2);}" % data_path,
                val='^#FORM._temp.data.layout.%s' % temp_path)

    @public_method
    def th_onLoading(self, record, newrecord, loadingParameters, recInfo):
        if newrecord:
            record['username'] = self.user
            record['data'] = Bag()
            record['data.main.page.height'] = 297
            record['data.main.page.width'] = 210
            record['data.main.page.top'] = 0
            record['data.main.page.bottom'] = 0
            record['data.main.page.left'] = 0
            record['data.main.page.right'] = 0
            record['data.main.design'] = 'headline'
            for i in ('top', 'center', 'bottom'):
                if i != 'center':
                    record.setItem('data.layout.%s' % i, None, height=30)
                for j in ('left', 'right'):
                    path = '%s.%s' % (i, j)
                    record.setItem('data.layout.%s' % path, None, width=30)

            for i in ('left', 'center', 'right'):
                if i != 'center':
                    record.setItem('data.layout.%s' % i, None, width=30)
                for j in ('top', 'bottom'):
                    path = '%s.%s' % (i, j)
                    record.setItem('data.layout.%s' % path, None, height=30)

    def th_options(self):
        return dict(dialog_height='630px',dialog_width='1100px',duplicate=True)
                          