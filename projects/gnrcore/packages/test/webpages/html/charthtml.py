# -*- coding: utf-8 -*-

"Test HTML DIV"

class GnrCustomWebPage(object):
    py_requires="gnrcomponents/testhandler:TestHandlerFull,gnrcomponents/source_viewer/source_viewer:SourceViewer" 
                
    def test_0_hardcoded(self,pane):
        pane.style("""
            .clsblock{
                background:lightgreen;
            }
            .clsblock.neg{
                background:red;
            }
            .ovf{
                background:green;
            }
            .ovf.neg{
                background:darkred;
            }
            .sottoscorta{
                background:orange;
            }
        
            .da_riordinare{
                background:blue;
            }
        """)
        data = self.datatest()
        valori = [d['value'] for d in data]
        ncol = len(data)
        valmin = min(valori)
        valmax = max(valori)
        val_ovf_max = 60
        val_ovf_min = -20
        wcol = 10
        widthpx = f'{wcol}px'
        colmargin = 2
        totwidth = (wcol+colmargin)*ncol
        ggscmin = 5
        punto_riordino = 20
        valmax = min(valmax,val_ovf_max)
        valmin = max(valmin,val_ovf_min)
        tot_height = val_ovf_max-val_ovf_min
        root = pane.div(_class='chartroot',height=f'{tot_height}px',width=f'{totwidth}px',
                        position='relative',margin='20px',border='1px solid #efefef')
        ax_x = -val_ovf_min
        box = root.div(top=0,bottom=f'{ax_x}px',
                    position='absolute',
                    left=0,right=0)
        currix = 0
        for d in data:
            h = d['value']
            clscontent = ''
            tip=f"{d['label']} gg {d['value']}"
            if h>val_ovf_max:
                h = val_ovf_max
                clscontent = 'ovf'
            elif h<0:
                clscontent = 'neg'
                if h<val_ovf_min:
                    h = val_ovf_min
                    clscontent = 'neg ovf'
            else:
                if h<ggscmin:
                    clscontent = 'sottoscorta'
                elif h<punto_riordino:
                    clscontent = 'da_riordinare'

            box.div(
                position='absolute',left=f'{currix}px',bottom=0 if h>0 else f'{h}px',
                        height=f'{abs(h)}px',
                        width=widthpx,_class=f'clsblock {clscontent}',tip=tip
            )
            currix += wcol+colmargin

    def datatest(self):
        return  [
            dict(label='2022-09',value=-10),
            dict(label='2022-10',value=40),
            dict(label='2022-11',value=12),
            dict(label='2022-12',value=3),
            dict(label='2022-13',value=-5),
            dict(label='2022-14',value=-8),
            dict(label='2022-15',value=6),
            dict(label='2022-16',value=30),
            dict(label='2022-17',value=40),
            dict(label='2022-18',value=50),
            dict(label='2022-19',value=60),
            dict(label='2022-20',value=100),
            dict(label='2022-21',value=40),
            dict(label='2022-22',value=8),
            dict(label='2022-23',value=2),
            dict(label='2022-24',value=20)
        ]

    def test_1_js(self,pane):
        box = pane.div(height='100px').div()
        val_ovf_max = 60
        val_ovf_min = -20
        pane.style("""
            .mc_positive.sscorta{
                background:orange;
            }
            .mc_positive.sriordino{
                background:blue;
            }
        """)
        ggscmin = 5
        punto_riordino = 20

        pane.button('Test').dataController("""genro.dom.microchart(data,{ovf_min:val_ovf_min,
                                                                    ovf_max:val_ovf_max,
                                                                    min_sscorta:ggscmin,
                                                                    min_sriordino:punto_riordino},box)""",
                                            val_ovf_min=val_ovf_min,val_ovf_max=val_ovf_max,
                                            ggscmin=ggscmin,punto_riordino=punto_riordino,
                                            box=box,data=self.datatest())
