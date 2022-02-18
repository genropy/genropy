# encoding: utf-8
def config(root,application=None):
    administration = root.branch(u"!!Administration", tags="admin")
    
    user_setup = administration.branch('!!Users setup')
    userSetup(user_setup,application=application)

    utility = administration.branch('!!App Utility',tags='admin')
    appUtility(utility,application)
   
    dev = administration.branch('!!Developers',tags='_DEV_')
    
    dev.webpage(u"!!Install Checklist", filepath="/adm/checklist_page")
    dev.thpage(u"!!Backups", table="adm.backup")


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


def userSetup(root,**kwargs):
    root.webpage(u"!!Users", filepath="/adm/user_page")
    root.thpage(u"!!Auth tags", table="adm.htag")
    root.thpage(u"!!Group", table="adm.group")
    root.thpage(u"!!Access groups", table="adm.access_group",tags='_DEV_,superadmin')
    root.webpage('!!User preferences',filepath='/adm/user_preference')

def appUtility(utility,**kwargs):
    utility.thpage(u"!!Letterheads", table="adm.htmltemplate")
    utility.thpage(u"!!Notifications", table="adm.notification")
    utility.thpage(u"!!Authorizations", table="adm.authorization")
    utility.thpage(u"!!Days", table="adm.day")
    utility.thpage(u"!!Userobjects", table="adm.userobject")
    utility.thpage(u"!!Counters", table="adm.counter",tags='_DEV_,superadmin')
    utility.lookups(u"!!Utility tables", lookup_manager="adm")
    utility.webpage('!!Application preferences',tags='admin',filepath='/adm/app_preference')
