#!/usr/bin/python3
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent

class View(BaseComponent):

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('date')

    def th_order(self):
        return 'date'

    def th_query(self):
        return dict(column='date', op='contains', val='')

class ViewCalendar(BaseComponent):
    
    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('date',hidden=True)
        r.fieldcell('dow',hidden=True)
        r.fieldcell('holiday',hidden=True)
        r.fieldcell('day_cal',width='100%')

    def th_top_custom(self,top):
        bar = top.bar.replaceSlots('#','*,btn,*',background='transparent',_class='')
        bar.btn.slotButton('XXX')


    def th_order(self):
        return 'date'

    def th_view(self,view):
        view.attributes['_class'] = f"{view.attributes['_class']} noselect noheader templateGrid"

class ViewIncluded(BaseComponent):
    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('date')

    def th_order(self):
        return 'date'


class Form(BaseComponent):

    def th_form(self, form):
        bc = form.center.borderContainer()
        fb = bc.contentPane(region='top',padding='10px',datapath='.record').formbuilder(cols=2, border_spacing='4px')
        fb.field('date')
        bc.contentPane(region='center').plainTableHandler(
            table='sys.calendar',nodeId='innercal',
            condition='$date=:mydate',
            condition_mydate='^#FORM.record.date',
            viewResource='ViewIncluded',
            view_store_aggregateRows=False
        )

    def th_options(self):
        return dict(dialog_height='400px', dialog_width='600px')
