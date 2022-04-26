# -*- coding: utf-8 -*-

"""dataController"""

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"
    
    def test_0_alert(self,pane):
        "Action can be specified in button or in dataController, which can be then nested."
        pane.button('Hello',action='alert(message)',message='Hello')
        pane.button('Hello again').dataController('alert(message);',message='Hello')

    def test_1_players(self, pane):
        "Insert player names, welcome message will be automatically triggered"
        self.playerBox(container = pane.div(datapath='.player_one'),
                       default_color='blue')
        
        self.playerBox(container = pane.div(datapath='.player_two'),
                       default_color='red')
        
        pane.dataController("""if (p1 && p2){
                                   var msg ="Welcome "+ p1 + " and "+ p2;
                                   alert(msg);
                               }""",p1='^player_one.name', p2='^player_two.name')
        
    def playerBox(self, container, default_color=None):
        #set default color
        container.data('.color', default_color)
        
        #box
        player_box = container.div(border_color='^.color',
                                border='2px solid',
                                width='300px',
                                margin='10px',
                                rounded=6)
        #title bar
        player_box.div(innerHTML='^.name',
                       background='^.color',
                       color = 'white',
                       text_align='center',
                       height='15px')
        
        #form
        pl_form = player_box.formbuilder(margin='10px')
        pl_form.textbox(value = '^.name', lbl = 'Name')
        pl_form.filteringSelect(value ='^.color',
                                values = 'red,green,blue,purple',
                                lbl = 'Color')

    def test_2_lightbutton_controller(self, pane):
        """Use of lightbutton (no style) to attach dataController
        Lightbutton differs in style from normal button, but it works in the same way.
        Here we attach a dataController directly to the button"""
        btn = pane.lightbutton('What time is it?')
        btn.dataController('var now = new Date().toISOString(); SET .time=now;')
        pane.div('^.time')

    def test_3_moving_obj(self, pane):
        "dataController sets random position of an object every millisecond"
        pane.script("rndt=function(a,b){return Math.floor(Math.random()*(b-a))+a}")
        pane.div('Enjoy your Genropy Tutorial', position='relative',
                 top='^.top',left='^.left',font_size='^.size',color='^.olor', 
                 transition='all 1s ease-in', height='200px')
        pane.dataController("""SET .size=rndt(24,48)+'px';
                               SET .top=rndt(0,120)+'px';
                               SET .left=rndt(0,120,48)+'px';
                               SET .color='rgb('+rndt(0,255)+','+rndt(0,255)+','+rndt(0,255)+')'
                             """,_timing=1)
    
    def test_4_calculation(self, pane):
        "Insert .000 bytes to show them automatically converted"
        pane.div(margin='15px',datapath='bytesconverter').h1('Bytes Converter')
        box=pane.div(width='400px',border='1px solid gray')
        fb = box.formbuilder(cols=2)
        fb.numberTextBox('^.bytes',lbl='Bytes',width='60px')
        fb.div('^.conv',lbl='-->',width='140px',color='#777',
               font_size='16px')
        fb.dataController("""
             var s = ['Bytes','KB','MB','GB','TB'];
             if (b == 0) return 'n/a';
             var i = parseInt(Math.floor(Math.log(b) / Math.log(1024)));
             SET .conv = (b / Math.pow(1024, i)).toFixed(1) + ' ' + s[[i]];""",
             b='^.bytes')
   
    def test_5_ask(self, pane):
        "Ask for parameters directly when triggering action"
        fb = pane.formbuilder(cols=1)
        btn = fb.button('Start quiz')
        btn.dataController("SET .name=name; SET .age=age; SET .city=city;", 
                            _ask=dict(title="Tell us more about you...",
                                fields=[dict(name="name", lbl="Name"),
                                        dict(name="age", tag='numbertextbox', lbl="Age"),
                                        dict(name="city", lbl="City")]))
        fb.div('Data you entered: ', hidden='^.name?=!#v')
        fb.textbox('^.name', lbl='Name', readOnly=True, hidden='^.name?=!#v')
        fb.numbertextbox('^.age', lbl='Age', readOnly=True, hidden='^.age?=!#v')
        fb.textbox('^.city', lbl='City', readOnly=True, hidden='^.city?=!#v')

    def test_6_ask(self,pane):
        "Ask for parameters directly when triggering action, press shift to show parameters dialog"
        pane.data('.pars.nome','Giovanni')

        pane.textbox(value='^.cognome',lbl='Cognome',default='Bianchi')
        
        pane.button('Hello again').dataController('genro.dlg.alert(message + cognome + || ' ' || + nome,"Pippo")', 
                                                message='Hello ',
                                                cognome='=.cognome',
                                                nome='=.pars.nome',
                                                _ask=dict(title='Complete parameters', 
                                                            _if='!nome || !size || _filterEvent("Shift")',
                                                            fields=[dict(name='nome',lbl='nome')]))