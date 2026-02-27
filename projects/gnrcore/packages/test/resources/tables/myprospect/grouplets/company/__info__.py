class GroupletTopic(object):
    def __info__(self):
        return dict(caption='Company Profile', priority=1,
                    template='<div>${<b>$overview.industry</b>}'
                             '${<span> ( $overview.company_size )</span>}</div>'
                             '<div>$team.decision_maker'
                             '${<span> - $team.decision_maker_role </span>}</div>'
                             '${<div>ERP: $infrastructure.current_erp</div>}')
