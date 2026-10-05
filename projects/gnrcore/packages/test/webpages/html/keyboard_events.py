# -*- coding: utf-8 -*-

"""Keyboard events: what a DOM KeyboardEvent carries

An input connected to `onkeydown`, `onkeypress` and `onkeyup` publishes
every event; a dataController writes its key fields into a Bag the grid
shows, newest first, the last ten kept.
"""


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_0_keyboard_events(self, pane):
        """Type in Test input: one row per event, keydown and keypress rows coloured; the checkboxes filter them"""
        pane.css('.event_type_keydown', "color:red;")
        pane.css('.event_type_keypress', "color:green;")
        bc = pane.borderContainer(datapath='.logger', height='400px')
        fb = bc.contentPane(region='top', border_bottom='1px solid silver').formbuilder(cols=4)
        fb.input(value='^.curval', lbl='Test input',
                 connect_onkeydown='genro.publish("log_event",{evt:$1});',
                 connect_onkeypress='genro.publish("log_event",{evt:$1});',
                 connect_onkeyup='genro.publish("log_event",{evt:$1});')

        fb.checkbox(value='^.keydown', label='onkeydown', default=True)
        fb.checkbox(value='^.keypress', label='onkeypress', default=True)
        fb.checkbox(value='^.keyup', label='onkeyup', default=True)

        fb.button('Clear', action='SET .logdata = null;SET .curval=null;')
        bc.dataController("""
                if(!data){
                    data = new gnr.GnrBag();
                }else{
                    data = data.deepCopy();
                }
                if(keydown && evt.type=='keydown' || keypress && evt.type=='keypress' || keyup && evt.type=='keyup'){
                    var row = new gnr.GnrBag();
                    columns.forEach(function(c){row.setItem(c,evt[c]) });
                    data.setItem('#id',row,{_customClasses:'event_type_'+evt.type},{_position:'<'});
                    if(data.len()>10){data.popNode('#11');}
                    SET .logdata = data;
                }
                evt.target.value = null;
            """, data='=.logdata', subscribe_log_event=True,
                          keydown='=.keydown',
                          keypress='=.keypress',
                          keyup='=.keyup',
                          columns=['type', 'key', 'code', 'shiftKey', 'altKey', 'ctrlKey', 'metaKey'])
        center = bc.contentPane(region='center', margin='2px')
        center.quickGrid(value='^.logdata')
