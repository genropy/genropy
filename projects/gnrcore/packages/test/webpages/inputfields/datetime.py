# -*- coding: utf-8 -*-

"DateTextBox and TimeTextBox"

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerBase"
    
    def test_0_dateTextBox(self, pane):
        "DateTextBox without popup, press button to set current date and time"
        fb=pane.formbuilder(cols=2)
        fb.button('Set Now',fire='newdate')
        fb.datetimeTextbox(value='^.datetime', lbl='Datetime', seconds=True)
        fb.dataController('SET .datetime = new Date();', _fired='^newdate')
        
    def test_1_timeTextBox(self, pane):
        "Default timetextbox to define timestamp"
        pane.timetextbox(value='^.ttb', lbl='Choose time')
        pane.div('^.ttb')

    def test_2_combine(self,pane):
        "Combine date and time in ISOformat with a dataController"
        fb = pane.formbuilder(border_spacing='3px', cols=3)
        fb.datetextbox(value='^.start_date', dtype='D', lbl='Start Date')
        fb.timetextbox(value='^.start_time', dtype='H', lbl='Start Time')
        fb.dataController('this.setRelativeData("^.start_ts",combineDateAndTime(d,t),{dtype:"DHZ"});',
                            d='^.start_date',t='^.start_time',_if='d&&t')
        fb.dataFormula('^.start', 'start_ts.toISOString()', start_ts='^.start_ts')
        fb.div('^.start')
        fb.datetextbox(value='^.end_date', dtype='D', lbl='End Date')
        fb.timetextbox(value='^.end_time', dtype='H', lbl='End Time')
        fb.dataController('this.setRelativeData("^.end_ts",combineDateAndTime(d,t),{dtype:"DHZ"});',
                        d='^.end_date',t='^.end_time',_if='d&&t')
        fb.dataFormula('^.end', 'end_ts.toISOString()', end_ts='^.end_ts')
        fb.div('^.end')

    def test_3_period_to(self, pane):
        """With period_to user can insert a starting week/month/year, and get ending period compiled automatically.
        E.g. Try using "last week", "may", "ten years ago"."""
        fb = pane.formbuilder(cols=2)
        fb.dateTextBox(value='^.date_from',lbl='Date from',period_to='.date_to')
        fb.dateTextBox(value='^.date_to',lbl='Date to')
