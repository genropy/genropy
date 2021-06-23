# -*- coding: utf-8 -*-

"Test Javascript"

class GnrCustomWebPage(object):
    py_requires="gnrcomponents/testhandler:TestHandlerFull,gnrcomponents/source_viewer/source_viewer:SourceViewer" 
    
    def test_0_connect(self,pane):
        "Enrich a div with a javascript function that changes div content if event occurs"
        pane.data('.messaggio', 'Click here')
        pane.div('^.messaggio', font_size='30px', height='200px', width='400px', rounded=12,
                    text_align='center', color='white', background='green', margin='20px',
                    connect_onclick="this.setRelativeData('.messaggio','Mi hai cliccato');",
                    connect_ondblclick="SET .messaggio = 'Mi hai doppio cliccato';")

        pane.data('.messaggio2', 'Try entering here')
        pane.div('^.messaggio2', font_size='30px', height='200px', width='400px', rounded=12,
                    text_align='center', color='white', background='orange', margin='20px',
                    connect_onmouseenter='this.updAttributes({font_size:"60px"})')

    def test_2_button(self,pane):
        "Set variable when event occurs (press button)"
        fb = pane.formbuilder()
        fb.textbox(value='^.nome',lbl='Nome')
        fb.textbox(value='^.cognome',lbl='Cognome')

        fb.button('Azione',
                        action="SET .messaggio = cognome+' '+nome;",
                        cognome='=.cognome', nome='=.nome')
        fb.div('^.messaggio',lbl='Messaggio')

    def test_3_button(self,pane):
        "Same as before, but with different syntax (get and set variable)"
        fb = pane.formbuilder()
        fb.textbox(value='^.nome',lbl='Nome')
        fb.textbox(value='^.cognome',lbl='Cognome')

        fb.button('Azione',
                        action="""SET .messaggio = GET .cognome+' '+GET .nome;"""
                        #this.setRelativeData('.messaggio',this.getRelativeData('.cognome')+' '+this.getRelativeData('.nome'))
                        )
        fb.div('^.messaggio',lbl='Messaggio')

    def test_4_button(self,pane):
        "Ask for parameters in dialog, and set variable"
        fb = pane.formbuilder()
        fb.button('Azione',
                    ask=dict(title='Dammi le info',
                            fields=[dict(name='nome',lbl='Nome'),
                                    dict(name='cognome',lbl='Cognome'),
                                    dict(name='sesso',lbl='Sesso',tag='filteringSelect',
                                        values='M:Maschio,F:Femmina')]),
                        action="""SET .messaggio = cognome +' '+ nome + ' - '+sesso;""")
        fb.div('^.messaggio',lbl='Messaggio')

    def test_5_button(self,pane):
        "Use Python variables in Javascript"
        fb = pane.formbuilder()
        box = fb.div(height='40px',width='40px',background='red')
        fb.button('Cambia colore',
                    action='box.updAttributes({background:"green"})',
                    box=box)

    def test_6_datacontroller(self,pane):
        "Increase existing value every second with a dataController and using parameter '_timing'"
        fb = pane.formbuilder()
        fb.numberTextBox(value='^.base',lbl='Base',default=0)
        pane.dataController("""SET .base = currbase + 1;""",
                                _timing=1,currbase='=.base')

    def test_7_dataFormula(self,pane):
        "Calculate area after inserting width and height with a dataFormula"
        fb = pane.formbuilder()
        fb.numberTextBox(value='^.base',lbl='Base',default=0)
        fb.numberTextBox(value='^.altezza',lbl='Altezza',default=0)
        fb.filteringSelect(value='^.poligono',lbl='Poligono',
                values='q:Quadrato,t:Triangolo',default='t')
        fb.div('^.area')
        pane.dataFormula('.area',"""poligono=='t'? base*altezza/2 : base*altezza;""",
                        base='^.base',
                        altezza='^.altezza',
                        poligono='^.poligono')
        
    
    def test_8_datacontroller(self,pane):
        "Calculate area and perimeter after inserting width and height with a dataController"
        fb = pane.formbuilder()
        fb.numberTextBox(value='^.base',lbl='Base',default=0)
        fb.numberTextBox(value='^.altezza',lbl='Altezza',default=0)
        fb.div('^.area',lbl='Area')
        fb.div('^.perimetro',lbl='Perimetro')
        pane.dataController("""SET .area = base * altezza;
                            SET .perimetro = (base+altezza)*2;""",
                        base='^.base',altezza='^.altezza')
    
    def test_video(self, pane):
        "This HTML events test was explained in this LearnGenropy video"
        pane.iframe(src="https://www.youtube.com/embed/aVyUlDy3nCE", width='240px', height='180px',
                        allow="autoplay; fullscreen")