# -*- coding: utf-8 -*-
#
#  Mail proxy dashboard page
#


class GnrCustomWebPage(object):
    py_requires = 'public:Public,gnrcomponents/framegrid:FrameGrid,mailproxy_dashboard:MailProxyDashboard'
    auth_main = 'admin'

    def windowTitle(self):
        return '!!Mail Proxy Dashboard'

    def main(self, root, **kwargs):
        bc = root.rootBorderContainer(datapath='main', title='!!Mail proxy dashboard')
        self.mp_proxy_layout(bc)
