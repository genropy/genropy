# -*- coding: utf-8 -*-

# th_user.py
# Created by Saverio Porcari on 2011-03-13.
# Copyright (c) 2011 Softwell. All rights reserved.

from gnr.web.gnrbaseclasses import BaseComponent


class View(BaseComponent):
    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('tag_id', width='20em')
        r.fieldcell('@tag_id.note', width='100%')
        
    def th_order(self):
        return 'tag_id'
        
    def th_query(self):
        return dict(column='tag_id',op='contains', val='')
       

class ViewFromUser(BaseComponent):
    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('tag_id', width='20em', edit=True)
        r.fieldcell('@tag_id.note', width='100%')
        
    def th_order(self):
        return 'tag_id'
        
   # def th_query(self):
   #     return dict(column='tag_code',op='contains', val='')
   #    


class ViewFromGroup(BaseComponent):
    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('tag_id', width='20em',edit=True)
        r.fieldcell('@tag_id.note', width='100%')
        
    def th_order(self):
        return 'tag_id'


class ViewFromTag(BaseComponent):
    def th_hiddencolumns(self):
        return '$user_id,$user,$group_code'
        
    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('user_or_group',width='20em')
        r.fieldcell('email',width='10em')
        
    def th_order(self):
        return 'user_or_group'
        
   #def th_query(self):
   #    return dict(column='user',op='contains', val='')
    
class Form(BaseComponent):
    
    def th_form(self, form):
        pane = form.record
        fb = pane.formbuilder(cols=2, border_spacing='4px')
        fb.field('tag_id')
        fb.field('user_id')

    def th_options(self):
        return dict(dialog_height='400px', dialog_width='600px')
