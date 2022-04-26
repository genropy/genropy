from gnr.web.gnrbaseclasses import BaseComponent
from gnr.web.gnrwebstruct import struct_method

class MsgArea(BaseComponent):

    def messageArea(self, parent, value=None, max_len=None, sound=None, color_ok=None, color_warning=None,
                            color_limit=None, auto_skip=None, height=None, width=None, **kwargs):
        box = parent.div(_workspace=True, **kwargs)
        box.textarea(value=value, height=height, width=width, _ml=max_len, _clrok=color_ok, 
                            _clrwg=color_warning, _snd=sound, _auto_skip=auto_skip,
                                                    connect_onkeyup="""var tgt = $1.target;
                                                        var my_text = tgt.value;
                                                        var currattr = this.currentAttributes();
                                                        var color_ok = currattr._clrok || 'grey';
                                                        var color_wg = currattr._clrwg || 'orange';
                                                        var max_len = currattr._ml || 80;
                                                        var remaining = max_len - my_text.length;
                                                        SET #WORKSPACE.rem = remaining;
                                                        SET #WORKSPACE.clr = (remaining<max_len/10)?color_wg:color_ok;
                                                        if(remaining<0){
                                                            if(currattr._snd){
                                                                genro.playSound(currattr._snd);
                                                            }
                                                            tgt.value = my_text.slice(0,max_len);
                                                            if(currattr._auto_skip){
                                                                tgt.blur()
                                                                return
                                                            }
                                                        }
                                                        """)
        last_line = box.div(font_style='italic', font_size='8pt')
        last_line.span('Remaining: ')
        last_line.span('^#WORKSPACE.rem', color='^#WORKSPACE.clr')
        
        return box

    @struct_method
    def mg_messageArea(self, parent, value=None, max_len=None, sound=None, color_ok=None, color_warning=None,
                            color_limit=None, auto_skip=None, height=None, width=None, **kwargs):
        box = parent.div(_workspace=True, **kwargs)
        box.textarea(value=value, height=height, width=width, _ml=max_len, _clrok=color_ok, 
                            _clrwg=color_warning, _snd=sound, _auto_skip=auto_skip,
                                                    connect_onkeyup="""var tgt = $1.target;
                                                        var my_text = tgt.value;
                                                        var currattr = this.currentAttributes();
                                                        var color_ok = currattr._clrok || 'grey';
                                                        var color_wg = currattr._clrwg || 'orange';
                                                        var max_len = currattr._ml || 80;
                                                        var remaining = max_len - my_text.length;
                                                        SET #WORKSPACE.rem = remaining;
                                                        SET #WORKSPACE.clr = (remaining<max_len/10)?color_wg:color_ok;
                                                        if(remaining<0){
                                                            if(currattr._snd){
                                                                genro.playSound(currattr._snd);
                                                            }
                                                            tgt.value = my_text.slice(0,max_len);
                                                            if(currattr._auto_skip){
                                                                tgt.blur()
                                                                return
                                                            }
                                                        }
                                                        """)
        last_line = box.div(font_style='italic', font_size='8pt')
        last_line.span('Remaining: ')
        last_line.span('^#WORKSPACE.rem', color='^#WORKSPACE.clr')
        
        return box