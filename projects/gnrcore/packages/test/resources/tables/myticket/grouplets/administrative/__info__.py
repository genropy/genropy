class GroupletTopic(object):
    def __info__(self):
        return dict(caption='Administrative', priority=3,
                    template='<div>${<span>Invoice: <b>$billing.invoice_number</b></span>}'
                             '${<span> | $billing.amount</span>}</div>'
                             '${<div>License: $licenses.license_type'
                             ' ( $licenses.user_count users)</div>}')
