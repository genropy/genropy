# -*- coding: UTF-8 -*-

class GnrCustomWebPage(object):
    py_requires = 'print_tutorial'

    def printContent(self,page,data=None):
        l = page.layout(top=1,left=1,
                    bottom=1,right=1,border_width=0.3)
        l.row().cell()
        s = l.row().cell().layout(top=20,left=20,
                                  right=20,
                                  bottom=10,border_width=0.3)
        l.row().cell()
        inner_row = s.row()
        inner_row.cell()
        inner_row.cell()
        s.row().cell()