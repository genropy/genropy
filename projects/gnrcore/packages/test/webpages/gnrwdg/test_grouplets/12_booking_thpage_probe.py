# -*- coding: utf-8 -*-

"""Menu-style thpage probe for the wizard center sizing: the same mechanism
a menu entry uses (rootTableHandler, dialog decided by the View's
th_options), on test.booking with the redtopic wizard. Open the dialog with
the window small, then enlarge the window: the red step must follow."""


class GnrCustomWebPage(object):
    py_requires = 'public:TableHandlerMain'
    maintable = 'test.booking'

    def windowTitle(self):
        return 'Booking thpage probe'

    def main(self, root, **kwargs):
        root.rootTableHandler(th_viewResource='ViewStack',
                              th_formResource='FormStack')
