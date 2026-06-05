from gnr.web.gnrbaseclasses import BaseComponent


class View(BaseComponent):

    def th_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('company_name', width='15em')
        r.fieldcell('contact_name', width='12em')
        r.fieldcell('contact_email', width='15em')
        r.fieldcell('source', width='8em')
        r.fieldcell('status', width='8em')

    def th_order(self):
        return 'company_name'

    def th_query(self):
        return dict(column='company_name', op='contains', val='')


class Form(BaseComponent):
    py_requires = 'gnrcomponents/grouplet/grouplet:GroupletHandler'

    def th_form(self, form):
        bc = form.center.borderContainer()
        top = bc.contentPane(region='top', datapath='.record')
        fb = top.formlet(cols=2, border_spacing='3px')
        fb.field('company_name', colspan=2, width='100%')
        fb.field('contact_name')
        fb.field('contact_email')
        fb.field('contact_phone')
        fb.field('source', tag='filteringSelect',
                 values='website:Website,referral:Referral,event:Event,'
                        'cold_call:Cold Call,other:Other')
        fb.field('status', tag='filteringSelect',
                 values='new:New,qualified:Qualified,proposal:Proposal,'
                        'won:Won,lost:Lost')
        bc.contentPane(region='center').groupletPanel(
            value='^#FORM.record.extra_data',
            table='test.myprospect',
            frameCode='prospect_panel')

    def th_options(self):
        return dict(dialog_windowRatio=.9)


class FormGrid(BaseComponent):
    """Alternative form using topic-grid: each topic rendered as a collapsible
    grid of grouplets instead of tree navigation."""
    py_requires = 'gnrcomponents/grouplet/grouplet:GroupletHandler'

    def th_form(self, form):
        bc = form.center.borderContainer()
        top = bc.contentPane(region='top', datapath='.record')
        fb = top.formlet(cols=2, border_spacing='3px')
        fb.field('company_name', colspan=2, width='100%')
        fb.field('contact_name')
        fb.field('contact_email')
        fb.field('contact_phone')
        fb.field('source', tag='filteringSelect',
                 values='website:Website,referral:Referral,event:Event,'
                        'cold_call:Cold Call,other:Other')
        fb.field('status', tag='filteringSelect',
                 values='new:New,qualified:Qualified,proposal:Proposal,'
                        'won:Won,lost:Lost')
        center = bc.contentPane(region='center', overflow='auto')
        for topic in ('company', 'needs', 'budget'):
            center.grouplet(
                resource=topic,
                table='test.myprospect',
                value='^#FORM.record.extra_data',
                remote_grid_collapsible=True,
                remote_grid_columns=2)

    def th_options(self):
        return dict(dialog_windowRatio=.9)
