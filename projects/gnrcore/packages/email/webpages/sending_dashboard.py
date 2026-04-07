# -*- coding: utf-8 -*-


class GnrCustomWebPage(object):
    maintable = 'email.message'
    py_requires = "public:Public,th/th:TableHandler,gnrcomponents/framegrid:FrameGrid,mailproxy_dashboard:MailProxyDashboard"

    def pageAuthTags(self, method=None, **kwargs):
        return 'admin'

    def main(self, root, **kwargs):
        has_proxy = bool(self.db.package('email').getMailProxy(raise_if_missing=False))
        bc = root.rootBorderContainer(datapath='main', title='!!Sending Dashboard')
        if has_proxy:
            self.mp_proxy_layout(bc)
        else:
            self._queue_layout(bc)

    # -------------------------------------------------------------------------
    # Queue layout (no proxy)
    # -------------------------------------------------------------------------
    def _queue_layout(self, bc):
        frame = bc.contentPane(region='top', height='40%', splitter=True).groupByTableHandler(
            table='email.message',
            title='Account sending status',
            frameCode='sending_dashboard',
            struct=self._queue_dashboard_struct,
            condition='$in_out=:io',
            condition_io='O',
            condition__onStart=True,
            condition__reloader='^main.reloadAccountSendingStatus',
            static=True,
            pbl_classes=False,
        )
        frame.top.bar.replaceSlots('#', '#,reload,5')
        frame.top.bar.reload.slotButton('!!Reload', iconClass='iconbox reload',
                                        action='FIRE main.reloadAccountSendingStatus;')
        bc.contentPane(region='center').plainTableHandler(
            table='email.message_to_send', view_store__onStart=True,
        )

    def _queue_dashboard_struct(self, struct):
        r = struct.view().rows()
        r.fieldcell('@account_id.account_name', name='!!Account', width='20em')
        r.cell('_grp_count', name='!!Total', width='6em', group_aggr='sum')
        r.fieldcell('in_queue', name='!!In queue', width='8em', group_aggr='sum')
        r.fieldcell('is_sent', name='!!Sent', width='8em', group_aggr='sum')
        r.fieldcell('is_error', name='!!Errors', width='8em', group_aggr='sum')
        r.fieldcell('queue_mismatch', name='!!Mismatch', width='8em', group_aggr='sum')
