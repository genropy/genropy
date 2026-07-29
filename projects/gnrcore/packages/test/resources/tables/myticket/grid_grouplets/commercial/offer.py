"""Commercial Offer ticket — complete grid row template.

Header: subject + status + ticket_date (common to all ticket grouplets).
Body: estimated_budget, offer_deadline, products_of_interest (offer-specific,
under .extra_data sub-Bag).
Footer: description (common).
"""
from gnr.web.gnrbaseclasses import BaseComponent


class Grouplet(BaseComponent):
    def __info__(self):
        return dict(caption='Offer', priority=2)

    def grouplet_main(self, pane, **kwargs):
        # Header: subject (titolo) + status pill + date
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
        # Body: campi specifici del tipo, dentro extra_data
        body = pane.div(datapath='.extra_data', padding='4px 0')
        fb = body.formlet(cols=2, border_spacing='3px')
        fb.numberTextBox(value='^.estimated_budget', lbl='Estimated Budget')
        fb.dateTextBox(value='^.offer_deadline', lbl='Offer Deadline')
        fb.textbox(value='^.products_of_interest',
                   lbl='Products of Interest',
                   colspan=2, width='100%')
        # Footer: description (comune)
        pane.simpleTextArea(value='^.description',
                            placeholder='!!Notes / description',
                            width='100%', height='40px',
                            border='1px solid #e5e5e5',
                            padding='4px 6px', font_size='12px',
                            margin_top='4px')
