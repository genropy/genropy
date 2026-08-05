"""Administrative Billing ticket — complete grid row template."""
from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Billing', priority=1)

    def grouplet_main(self, pane, **kwargs):
        head = pane.div(_class='gg-ticket-head', display='grid',
                        grid_template_columns='1fr auto', gap='8px',
                        align_items='center', padding='4px 0 6px 0')
        title = head.div(display='flex', flex_direction='column', gap='2px')
        title.textbox(value='^.subject', placeholder='!!Subject',
                      lbl=None, font_weight='600', font_size='14px',
                      border='none', background='transparent',
                      padding='2px 0', width='100%')
        title.dateTextBox(value='^.ticket_date', lbl='Date', width='10em')
        head.filteringSelect(value='^.status', lbl='Status', width='8em',
                             values='open:Open,in_progress:In Progress,closed:Closed',
                             _class='gg-ticket-status-pill')
        body = pane.div(datapath='.extra_data', padding='4px 0')
        fb = body.formlet(cols=2, border_spacing='3px')
        fb.textbox(value='^.invoice_number', lbl='Invoice Number')
        fb.numberTextBox(value='^.amount', lbl='Amount')
        fb.dateTextBox(value='^.due_date', lbl='Due Date')
        pane.simpleTextArea(value='^.description',
                            placeholder='!!Notes / description',
                            width='100%', height='40px',
                            border='1px solid #e5e5e5',
                            padding='4px 6px', font_size='12px',
                            margin_top='4px')
