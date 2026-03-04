# -*- coding: utf-8 -*-

# Created by Francesco Porcari on 2011-03-31.
# Copyright (c) 2011 Softwell. All rights reserved.

from gnr.web.gnrbaseclasses import BaseComponent

class TestComunePiuBello(BaseComponent):
    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('denominazione', width='20em',edit=True
            )
        r.checkboxcolumn(radioButton=True,checkedId='#FORM.comunePiuBello')

class TestViewVotoRadio(BaseComponent):
    def th_struct(self,struct):
        r = struct.view().rows()
        r.checkboxcolumn('capoluogo',name='C',radioButton=True)
        r.fieldcell('denominazione', width='20em',edit=True)

        voto = r.columnset('voto',name='Votazione')
        voto.checkboxcolumn('voto_si',radioButton='voto',
                        name=u'Sì',width='4em')
        voto.checkboxcolumn('voto_no',radioButton='voto',
                        name='No',width='4em')
        voto.checkboxcolumn('voto_astenuto',radioButton='voto',
                        name='Ast.',width='4em')

        meteo = r.columnset('meteo',name='Meteo',background='darkgreen')
        meteo.checkboxcolumn('brutto',radioButton='mt',
                        name=u'Brutto',width='4em')
        meteo.checkboxcolumn('bello',radioButton='mt',
                        name='Bello',width='4em')
        meteo.checkboxcolumn('medio',radioButton='mt',
                        name='Medio',width='4em')

        pop = r.columnset('pop',name='Popolazione')

        pop.cell('n_voti_si',calculated=True,width='7em',
                formula='voto_si?popolazione_residente:0',dtype='L',
                name=u'Sì',totalize='#FORM.record.mill_si',format='#,###,###')

        pop.cell('n_voti_no',calculated=True,width='7em',
            totalize='#FORM.record.mill_no',
                formula='voto_no? popolazione_residente:0',
                dtype='L',name='No',format='#,###,###')
        pop.cell('n_voti_astenuto',calculated=True,width='7em',
            totalize='#FORM.record.mill_ast',
                formula='voto_astenuto?popolazione_residente:0',
                    dtype='L',name='Astenuti',format='#,###,###')
        pop.cell('n_voti_assenti',calculated=True,width='7em',
                formula='!(voto_astenuto||voto_si||voto_no)?popolazione_residente:0',
                    dtype='L',name='Assenti',totalize=True,format='#,###,###')
        pop.fieldcell('popolazione_residente', width='7em',
            name='Totale',totalize=True,format='#,###,###')

    def th_order(self):
        return 'denominazione'


    def th_view(self,view):
        grid = view.grid
        f = grid.footer(background_color='#B0CCEB')
        f.item('denominazione',value='Percentuali',colspan=4,text_align='right')
        f.item('n_voti_si',value='^.perc.voti_si',text_align='right',format='##.00')
        f.item('n_voti_no',value='^.perc.voti_no',text_align='right',format='##.00')
        f.item('n_voti_astenuto',value='^.perc.voti_astenuti',text_align='right',format='##.00')
        f.item('n_voti_assenti',value='^.perc.voti_assenti',text_align='right',format='##.00')
        f.item('popolazione_residente',value='100.00',text_align='right')
        view.grid.dataController("""
            var si = Math.round10(n_voti_si*100/n_voti_totali,-2);
            var no =  Math.round10(n_voti_no*100/n_voti_totali,-2);
            var ast = Math.round10(n_voti_astenuti*100/n_voti_totali,-2);
            SET .perc.voti_si = si;
            SET .perc.voti_no = no;
            SET .perc.voti_astenuti = ast;
            SET .perc.voti_assenti = 100-si-no-ast;
            """,n_voti_si='^#FORM.record.mill_si',
                n_voti_no='^#FORM.record.mill_no',
                n_voti_astenuti='^#FORM.record.mill_ast',
                n_voti_totali='^.totalize.popolazione_residente',_delay=1)

        view.top.bar.replaceSlots('vtitle','vtitle,filterset@per_voto')

    def th_filterset_per_voto(self):
        return [dict(code='tutti',caption='Tutti'),
                dict(code='voto_si',caption=u'Sì',cb='voto_si'),
                dict(code='voto_no',caption=u'No',cb='voto_no',isDefault=True),
                dict(code='voto_ast',caption=u'Astenuti',cb='voto_astenuto'),
                dict(code='voto_ass',caption=u'Assenti',cb='!(voto_si || voto_no || voto_astenuto)')
                ]


    def th_options(self):
        return dict(grid_footer='Totali Voto')

class ViewTestSections(BaseComponent):

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('denominazione', width='20em')
        r.fieldcell('@sigla_provincia.@regione.zona', hidden=True)

    def th_sections_zone(self):
        return [dict(code='nord',caption='!!Nord',condition='@sigla_provincia.@regione.zona=:zona_ovest OR @sigla_provincia.@regione.zona=:zona_est',
                                condition_zona_ovest='Nord-ovest', condition_zona_est='Nord-est'),
                dict(code='centro',caption='!!Centro',condition='@sigla_provincia.@regione.zona=:zona',condition_zona='Centro'),
                dict(code='sud',caption='!!Sud',condition='@sigla_provincia.@regione.zona=:zona',condition_zona='Sud'),
                dict(code='isole',caption='!!Isole',condition='@sigla_provincia.@regione.zona=:zona',condition_zona='Isole')
                ]

    def th_top_custom(self,top):
        top.bar.replaceSlots('#','searchOn,sections@zone,*')

    def th_options(self):
        return dict(virtualStore=False)

class ViewTestQuery(BaseComponent):
    
    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('denominazione', width='20em')
        r.fieldcell('popolazione_residente')

    def th_queryBySample(self):
        return dict(fields=[dict(field='$denominazione', lbl='Denominazione :',width='10em'),
                    dict(field='$popolazione_residente', lbl='pop_resid <',width='10em', op='less', val=''),
                    dict(field='$popolazione_residente', lbl='pop_resid >=',width='10em', op='greatereq', val='')],
                    cols=3, isDefault=True)

class ViewTestQueryCondition(BaseComponent):
    
    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('denominazione', width='20em')
        r.fieldcell('sigla_provincia')

    def th_queryBySample(self):
        return dict(fields=[dict(field='$denominazione', lbl='Denominazione',width='10em'),
                    dict(field='$sigla_provincia', lbl='Provincia', width='6em', table='glbl.provincia', 
                            condition='$regione=:rlom', condition_rlom='LOM', 
                            tag='checkboxtext', popup=True)],
                    cols=2, isDefault=True)
