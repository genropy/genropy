"""Kanban card — title + assignee + priority badge.

Used by `test_8_kanban_board` in 11_grouplet_grid.py to demonstrate
cross-grid drag-and-drop with a realistic narrative (move tasks across
workflow lanes).
"""
from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Kanban Card', priority=22)

    def grouplet_main(self, pane, **kwargs):
        card = pane.div(display='flex', flex_direction='column', gap='4px')
        card.textbox(value='^.title',
                     placeholder='!!Task title',
                     lbl=None,
                     font_weight='600', font_size='13px',
                     border='none', background='transparent',
                     padding='2px 0', width='100%')
        meta = card.div(display='flex', gap='6px', align_items='center',
                        font_size='11px', color='#666')
        meta.div('^.assignee',
                 padding='1px 6px',
                 background='var(--surface-alt, #eef1f4)',
                 border_radius='10px',
                 white_space='nowrap')
        # Priority pill: colour-coded (low/med/high). Colour is computed
        # client-side via a `=` dynamic-attr expression on the value.
        meta.div('^.priority',
                 padding='1px 6px',
                 border_radius='10px',
                 font_weight='600',
                 text_transform='uppercase',
                 letter_spacing='0.4px',
                 background=('=.priority=="high"?"#fdecea":'
                             '.priority=="med"?"#fff5e0":"#e8f4ec"'),
                 color=('=.priority=="high"?"#b53024":'
                        '.priority=="med"?"#a07412":"#2c7846"'))
