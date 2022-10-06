# encoding: utf-8
class Menu(object):
    def config(self,root):
        administration = root.branch(u"!!Administration", tags="admin")
        user_setup = administration.branch('!!Users setup')
        self.userSubmenu(user_setup)
        utility = administration.branch('!!App Utility',tags='admin')
        self.utilitySubmenu(utility)
        self.developerSubmenu(administration.branch('!!Developers',tags='_DEV_'))
        
        access_history = administration.branch('Access history',tags='_DEV_',checkpref='adm.dev.connection_log_enabled')
        access_history.thpage(u"!!Connections", table="adm.connection")
        access_history.thpage(u"!!Served pages", table="adm.served_page")
        permissions = administration.branch('!!Access permissions',tags='superadmin,_DEV_')
        permissions.thpage(u"!!Pkginfo", table="adm.pkginfo")
        permissions.thpage(u"!!Tableinfo", table="adm.tblinfo")
        permissions.webpage(u"!!User configurator", filepath="/adm/user_configuration",tags='superadmin')
        unused = administration.branch('!!Unused',tags='_DEV_')
        unused.thpage(u"!!Menu Manager", table="adm.menu")
        unused.thpage(u"!!Menu Pages", table="adm.menu_page")
        unused.thpage(u"!!Sent email", table="adm.sent_email")


    def userSubmenu(self,root,**kwargs):
        root.thpage(u"!!Users", table="adm.user")
        root.thpage(u"!!Auth tags", table="adm.htag")
        root.thpage(u"!!Group", table="adm.group")
        root.thpage(u"!!Access groups", table="adm.access_group",tags='_DEV_,superadmin')
        root.webpage('!!User preferences',filepath='/adm/user_preference')

    def utilitySubmenu(self,utility,**kwargs):
        utility.thpage(u"!!Letterheads", table="adm.htmltemplate")
        utility.thpage(u"!!Notifications", table="adm.notification")
        utility.thpage(u"!!Authorizations", table="adm.authorization")
        utility.thpage(u"!!Days", table="adm.day")
        utility.thpage(u"!!Userobjects", table="adm.userobject")
        utility.thpage(u"!!Counters", table="adm.counter",tags='_DEV_,superadmin')
        utility.lookups(u"!!Utility tables", lookup_manager="adm")
        utility.webpage('!!Application preferences',tags='admin',filepath='/adm/app_preference')

    def developerSubmenu(self,dev,**kwargs):
        dev.webpage(u"!!Install Checklist", filepath="/adm/checklist_page")
        dev.thpage(u"!!Backups", table="adm.backup")