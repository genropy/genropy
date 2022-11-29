#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method
from gnr.core.gnrbag import Bag
from gnr.core.gnrhtml import GnrHtmlBuilder

class PrintTutorial(BaseComponent):
    print_table = None
    record_mode = False
    py_requires = 'gnrcomponents/source_viewer/source_viewer'
    source_viewer_rebuild = False

    def main(self,root,**kwargs):
        root.attributes['overflow'] = 'hidden'
        frame = root.framePane(frameCode='print_tutorial',datapath='main')
        bar = frame.top.slotToolbar('5,vtitle,2,selector,*,reload,50',vtitle='Print Tester',height='20px')
        if self.print_table and self.record_mode:
            fb = bar.selector.formbuilder(cols=1,border_spacing='3px')
            fb.dbSelect(value='^.record_id',dbtable=self.print_table,lbl='Record %s' %self._(self.db.table(self.print_table).name_long))
        else:
            bar.selector.div()
        bar.reload.slotButton('Make',action='FIRE .run;')
        bc = frame.center.borderContainer()
        top = bc.borderContainer(region='top', height='150px', margin='5px')
        top.contentPane(region='top').div(
        """Please set page parameters and press "Make" to build HTML and PDF resources.\n
        You can customize and test your layout by pressing "Code" on the right""")
        fb = top.contentPane(region='center').formbuilder(
                                        datapath='page_pars',fld_width='4em',cols=2)
        fb.numberTextBox('^.page_height',lbl='Page height',default=297)
        fb.numberTextBox('^.page_width',lbl='Page width',default=210)
        fb.numberTextBox('^.page_margin_top',lbl='Page margin top')
        fb.numberTextBox('^.page_margin_left',lbl='Page margin left')
        fb.numberTextBox('^.page_margin_right',lbl='Page margin right')
        fb.numberTextBox('^.page_margin_bottom',lbl='Page margin bottom')

        center = bc.tabContainer(region='center',margin='2px')
        bar.dataRpc(self.print_tutorial_content,
                        pars='=page_pars',
                        lib='=library',
                        rpc_record_id='^.record_id',
                        _onResult="""
                            SET .htmlsource = result.getItem('htmlsource');
                            SET .pdfsrc = result.getItem('pdfsrc')+'?='+(new Date().getTime());
                        """,_fired='^.run',subscribe_rebuildPage=True)
        center.contentPane(title='Source HTML',overflow='hidden').codemirror(value='^.htmlsource',readOnly=True,
                        config_mode='htmlmixed',config_lineNumbers=True,height='100%')
        center.contentPane(title='HTML',overflow='hidden').iframeDiv(value='^.htmlsource',height='100%',width='100%')
        center.contentPane(title='PDF',overflow='hidden').iframe(src='^.pdfsrc',height='100%',width='100%',border=0)

    @public_method
    def print_tutorial_content(self,record_id=None,pars=None,lib=None,**kwargs):
        pars = pars or Bag()
        builder = GnrHtmlBuilder(**pars.asDict())
        builder.initializeSrc()
        builder.styleForLayout()
        builder.head.style("""
            .paper_layout{
                background:#efefef;
            }
        """)
        data = Bag()
        if self.print_table:
            if self.record_mode:
                if record_id:
                    data = self.db.table(self.print_table).record(pkey=record_id).output('bag')
            else:
                data = self.db.table(self.print_table).query().selection().output('records')
        self.printContent(builder.newPage(),data=data)
        result = Bag()
        result['htmlsource'] = builder.toHtml()
        builder.toPdf(self.site.getStaticPath('page:testpdf','preview.pdf',autocreate=-1))
        result['pdfsrc'] = self.site.getStaticUrl('page:testpdf','preview.pdf')
        return result

    def printContent(self,body,data=None):
        pass

