# -*- coding: utf-8 -*-

from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method

class FiltersDialog(BaseComponent):
    
    def filterSlotButton(self, slot, datapath=None, condition=None, filters=None, **kwargs):
        dlg = self.filtersDialog(slot, datapath=datapath, condition=condition, filters=filters, **kwargs)
        slot.slotButton(_class='google_icon filters', background='#555', height='35px').dataController(
                                    "dlg.show();", dlg=dlg.js_widget)
        
    def filtersDialog(self, pane, datapath=None, condition=None, filters=None, **kwargs):
        if condition:
            base_condition = condition.pop('condition')
            base_condition_kwargs = condition
        filter_condition_kwargs = {}
        dlg = pane.dialog(title='!![en]Filter messages', width='320px', height='130px', top='300px', 
                                    datapath=datapath or 'messageFilters', closable=True)
        fb = dlg.mobileFormBuilder(cols=2, border_spacing='4px', padding='5px')
        for filter in filters:
            filter_condition = filter.pop('filter_condition', None)
            if filter_condition:
                filter_condition_kwargs.update({f"condition_{filter}":f"^.{filter}"})
            fb.child(value=f"^.{filter.pop('name',None)}", tag=filter.pop('tag', None), 
                            lbl=filter.pop('lbl', None), **filter)
        dlg.dataController("""var condition_list = [base_condition];
                                filters.forEach(function(filter) {
                                    var fieldValue = this.getValue("." + filter.name);
                                    if (fieldValue && filter.filter_condition) {
                                        condition_list.push(filter.filter_condition);
                                    }
                                }, this);

                                var condition = condition_list.join(" AND ");
                                SET .condition = condition;""", 
                            filters=filters, base_condition=base_condition, 
                            **filter_condition_kwargs, **base_condition_kwargs, _onStart=True)
        return dlg
    
                        