class GroupletTopic(object):
    def __info__(self):
        return dict(caption="Mobile App", iconClass="appstore", priority=2,
                    template='<div>${<span>iOS: <b>$ios_qrcode.app_name</b></span>}'
                             '${<span> ( $ios_qrcode.device_target )</span>}</div>'
                             '${<div>Android: $android_qrcode.app_name'
                             ' | SDK $android_qrcode.min_sdk_version</div>}'
                             '${<div>Server: $connection_qrcode.server_url'
                             ':$connection_qrcode.port</div>}')
