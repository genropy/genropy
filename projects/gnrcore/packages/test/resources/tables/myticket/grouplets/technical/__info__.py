class GroupletTopic(object):
    def __info__(self):
        return dict(caption='Technical', priority=1,
                    template='<div>${<span>OS: <b>$system.operating_system</b></span>}'
                             '${<span> | v$system.software_version</span>}</div>'
                             '${<div>Error: $error.error_code'
                             ' - $error.error_message</div>}')
