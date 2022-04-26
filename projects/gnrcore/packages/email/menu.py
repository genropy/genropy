# encoding: utf-8
class Menu(object):
    def config(self,root,**kwargs):
        email_config = root.branch(u"!!Email Config", tags="admin")
        email_config.thpage(u"!!Accounts", table="email.account", tags="")
        email_config.thpage(u"!!Messages", table="email.message", tags="")
        email_config.lookups(u"!!Utility tables", lookup_manager="email")

