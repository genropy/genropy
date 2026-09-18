"""Kanban card — title + assignee + priority + due date, all editable
inline. Used by `test_8_kanban_board` for cross-grid drag-and-drop.

Design: title on top, then a meta row with priority pill (filtering
select), assignee (textbox), and due date (dateTextBox).
"""
from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Kanban Card', priority=22)

    def grouplet_main(self, pane, **kwargs):
        card = pane.div(display='flex', flex_direction='column', gap='4px')
        # Title — bold, full width, no border (in-place editing).
        card.textbox(value='^.title',
                     placeholder='!!Task title',
                     lbl=None,
                     font_weight='600', font_size='13px',
                     border='none', background='transparent',
                     padding='2px 0', width='100%')
        # Meta row.
        meta = card.div(display='flex', gap='6px', align_items='center',
                        font_size='11px', color='#666',
                        flex_wrap='wrap')
        # Priority — coloured emoji dot in front of the level label.
        meta.filteringSelect(
            value='^.priority',
            values='🟢 low:low,🟡 med:med,🔴 high:high',
            width='90px',
            lbl=None)
        # Assignee — short textbox.
        meta.textbox(value='^.assignee',
                     placeholder='!!@assignee',
                     lbl=None,
                     width='110px',
                     border='none',
                     background='var(--surface-alt, #eef1f4)',
                     border_radius='10px',
                     padding='2px 8px')
        # Due date — compact picker.
        meta.dateTextBox(value='^.due',
                         lbl=None,
                         width='110px')
