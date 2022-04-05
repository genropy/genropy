# encoding: utf-8
class Menu(object):
    def config(self,root,**kwargs):
        flib = root.branch(u"!!Flib", tags="admin")
        flib.thpage(u"!!Categories", table="flib.category", tags="")
        flib.webpage(u"!!Uploader", tags="", filepath="/flib/item_uploader")
        flib.thpage(u"!!Items", table="flib.item", tags="")

