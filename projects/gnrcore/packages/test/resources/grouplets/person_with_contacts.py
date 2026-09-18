"""Person card with nested contact channels — realistic team roster
shape: avatar (initials) + name + role + team, then a nested
groupletGrid of contact channels.
"""
from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Team Member', priority=20)

    def grouplet_main(self, pane, **kwargs):
        head = pane.div(_class='gg-person-head',
                        display='grid',
                        grid_template_columns='auto 1fr auto',
                        gap='10px',
                        align_items='center',
                        padding='4px 0 8px 0')
        # Avatar = initials of `name`, computed via dataFormula.
        head.div('^.initials',
                 _class='gg-person-avatar',
                 width='34px', height='34px',
                 border_radius='50%',
                 background='var(--accent-color, #4a7bc8)',
                 color='white',
                 font_weight='600',
                 display='flex',
                 align_items='center',
                 justify_content='center',
                 font_size='13px')
        pane.dataFormula(
            '.initials',
            "(name||'').split(/\\s+/)"
            ".filter(function(p){return p;})"
            ".slice(0,2)"
            ".map(function(p){return p[0].toUpperCase();})"
            ".join('')",
            name='^.name')
        # Name + role/team stacked
        idblock = head.div(display='flex', flex_direction='column', gap='2px')
        idblock.textbox(value='^.name', placeholder='!!Full name',
                        lbl=None,
                        font_weight='600', font_size='14px',
                        border='none', background='transparent',
                        padding='2px 0', width='100%')
        meta = idblock.div(display='flex', gap='8px', align_items='center')
        meta.textbox(value='^.role', placeholder='!!Role',
                     lbl=None, width='130px',
                     border='none', background='transparent',
                     padding='2px 0', color='#666', font_size='12px')
        meta.div('·', color='#aaa', font_size='12px')
        meta.textbox(value='^.team', placeholder='!!Team',
                     lbl=None, width='130px',
                     border='none', background='transparent',
                     padding='2px 0', color='#666', font_size='12px',
                     font_style='italic')
        # Nested grid of contact channels.
        pane.div('Contact channels',
                 color='#888', font_size='11px', font_weight='600',
                 text_transform='uppercase', letter_spacing='0.4px',
                 margin='4px 0 2px 0')
        # Nested contacts grid: phantom '+ New contact' in the quieter
        # minimal style (no dashed border) — distinguishes the nested
        # add affordance from the outer "+ New team member" CTA.
        # kebab handles per-row actions (incl. delete); no top-right `×`.
        pane.groupletGrid(
            storepath='.contacts',
            resource='contact_row',
            delitem=False, editmenu=True,
            dragCode='contacts',
            additem_label='!!New contact',
            additem_class='grouplet_grid_footer--minimal',
            defaultRow=dict(channel='email', value=''))
