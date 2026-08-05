# encoding: utf-8
class Menu(object):
    def config(self,root,**kwargs):
        documentation = root.branch(u"!!Documentation", tags="_DOC_,_DEV_")
        documentation.thpage(u"!!Documentation", table="docu.documentation", tags="")
        documentation.thpage(u"!!Contents", table="docu.content", tags="")
        documentation.thpage(u"!!Handbooks", table="docu.handbook", tags="")
        documentation.thpage(u"!!Redirects", table="docu.redirect", tags="")
        documentation.lookupBranch(u"!!Docu tables", pkg="docu")
        faqs = documentation.branch(u"!!FAQs")
        faqs.thpage(u"!!FAQs Submission", table="docu.faq_area", tags="")
        faqs.thpage(u"!!FAQs Consultation", table="docu.faq", viewResource='ViewPublic', tags="")

