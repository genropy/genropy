class GroupletTopic(object):
    def __info__(self):
        return dict(caption='Commercial', priority=2,
                    template='<div>${<b>$company.company_name</b>}'
                             '${<span> ( $company.company_size )</span>}</div>'
                             '${<div>Budget: $offer.estimated_budget'
                             ' | $contract.contract_type contract</div>}')
