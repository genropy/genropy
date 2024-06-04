#!/usr/bin/python3
# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method


class View(BaseComponent):

    def th_struct(self,struct):
        r = struct.view().rows()
        r.fieldcell('content_id')
        r.fieldcell('version', width='3em')
        r.fieldcell('__ins_user', width='auto')
        r.fieldcell('__ins_ts', width='9em')

    def th_order(self):
        return 'content_id'

    def th_query(self):
        return dict(column='content_id', op='contains', val='')

    def th_view(self, view):
        view.dataController("""var versions = versions;
                                if(versions.length<2){
                                    return null; 
                                }else{
                                    var textToCheck = versions.split(',');
                                };
                                var diff = Diff.diffWords(textToCheck[0], textToCheck[1]);
                                var outputDiv = document.getElementById('diff-output');

                                diff.forEach((part) => {
                                  var color = part.added ? 'darkgreen' :
                                    part.removed ? 'red' : 'black';
                                  var span = document.createElement('span');
                                  span.style.color = color;
                                  span.appendChild(document.createTextNode(part.value));
                                  outputDiv.appendChild(span);
                                });
                                SET #FORM.diff=outputDiv;
                            """, 
                            versions='^.grid.currentSelectedPkeys', _if='versions')

class Form(BaseComponent):

    def th_form(self, form):
        pane = form.record
        fb = pane.formbuilder(cols=2, border_spacing='4px')
        fb.field('content_id')
        fb.field('version')
        fb.field('text')


    def th_options(self):
        return dict(dialog_height='400px', dialog_width='600px')


class FormDiff(BaseComponent):

    def th_form(self, form):
        pane = form.record
        pane.div(width='100%', height='100%', overflow='hidden').simpleTextArea(
                        value='^.text', width='100%', height='100%')
        
    def th_options(self):
        return dict(showtoolbar=False, readOnly=True)