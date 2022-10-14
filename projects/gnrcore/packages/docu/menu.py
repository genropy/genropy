# encoding: utf-8
class Menu(object):
    def config(self,root,**kwargs):
        documentation = root.branch(u"!!Documentation", tags="_DOC_")
        documentation.thpage(u"!!Documentation", table="docu.documentation", tags="")
        documentation.thpage(u"!!Handbooks", table="docu.handbook", tags="")
        documentation.thpage(u"!!Redirects", table="docu.redirect", tags="")
        documentation.lookupBranch(u"!!Docu tables", pkg="docu")

