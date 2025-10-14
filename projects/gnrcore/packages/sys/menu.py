# encoding: utf-8
class Menu(object):
    def config(self,root,**kwargs):
        system = root.branch(u"!!System", tags="sysadmin,_DEV_,superadmin")
        system.webpage("!!One Ring", tags="", filepath="/sys/onering")
        system.thpage("!!Errors", table="sys.error", tags="")
        system.thpage("!!Batch log", table="sys.batch_log", tags="")
        system.thpage("!!Upgrades", table="sys.upgrade", tags="")
        system.thpage("!!Services", table="sys.service", tags="")
        system.thpage("!!Tasks", table="sys.task", tags="_DEV_")
        system.webpage("!!Mobile App Check", filepath="/sys/mobileappcheck", tags="_DEV_,sysadmin,superadmin")
        system.webpage("!!Db Structure", tags="", filepath="/sys/dbstruct")
        system.webpage("!!Logging", tags="_DEV_", filepath="/sys/logging")
        system.webpage("!!Startup data manager", tags="_DEV_", filepath="/sys/startupdata_manager")
        system.webpage("!!Package editor", tags="_DEV_", filepath="/sys/package_editor")
        system.webpage("!!Localization editor", tags="_DEV_,_TRD_,superadmin", filepath="/sys/localizationeditor")
        system.webpage("!!GnrIDE", tags="_DEV_", filepath="/sys/gnride")
        system.webpage("!!POD dashboard", tags="_DEV_", filepath="/sys/pod_dashboard")
        system.thpage("!!Widgets", table="sys.widget", tags="")

