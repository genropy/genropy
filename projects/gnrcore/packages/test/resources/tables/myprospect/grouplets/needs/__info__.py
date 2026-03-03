class GroupletTopic(object):
    def __info__(self):
        return dict(caption='Needs Assessment', priority=2,
                    template='<div>${<span>Urgency: <b>$pain_points.urgency</b></span>}'
                             '${<span> | $pain_points.impact_area</span>}</div>'
                             '${<div>$goals.short_term_goals</div>}')
