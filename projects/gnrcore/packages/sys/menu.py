# encoding: utf-8
class Menu(object):
    def config(self,root,**kwargs):
        system = root.branch(u"!!System", tags="sysadmin,_DEV_,superadmin")
        system.webpage(u"Onering", tags="", filepath="/sys/onering")
        system.thpage(u"Errors", table="sys.error", tags="")
        system.thpage(u"Batch log", table="sys.batch_log", tags="")
        system.thpage(u"Upgrades", table="sys.upgrade", tags="")
        system.thpage(u"Services", table="sys.service", tags="")
        system.thpage(u"Tasks", table="sys.task", tags="_DEV_")
        system.webpage(u"Db Structure", tags="", filepath="/sys/dbstruct")
        system.webpage(u"Startup data manager", tags="_DEV_", filepath="/sys/startupdata_manager")
        system.webpage(u"Package editor", tags="_DEV_", filepath="/sys/package_editor")
        system.webpage(u"Localization editor", tags="_DEV_,_TRD_,superadmin", filepath="/sys/localizationeditor")
        system.webpage(u"GnrIDE", tags="_DEV_", filepath="/sys/gnride")
        system.webpage(u"POD dashboard", tags="_DEV_", filepath="/sys/pod_dashboard")
        system.thpage(u"Widgets", table="sys.widget", tags="")

