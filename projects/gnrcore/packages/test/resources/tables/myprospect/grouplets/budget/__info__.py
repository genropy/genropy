class GroupletTopic(object):
    def __info__(self):
        return dict(caption='Budget & Timeline', priority=3,
                    template='<div>${<span>Budget: <b>$financials.budget_range</b></span>}'
                             '${<span> ( $financials.budget_status )</span>}</div>'
                             '${<div>Start: $timeline.desired_start'
                             ' | $timeline.rollout_approach</div>}'
                             '${<div>Stage: $decision.decision_stage</div>}')
