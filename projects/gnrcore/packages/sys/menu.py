# encoding: utf-8
class Menu(object):
    def config(self,root,**kwargs):
        system = root.branch("!!System", tags="sysadmin,_DEV_,superadmin")
        system.webpage("Onering", tags="", filepath="/sys/onering")
        system.thpage("Errors", table="sys.error", tags="")
        system.thpage("Batch log", table="sys.batch_log", tags="")
        system.thpage("Upgrades", table="sys.upgrade", tags="")
        system.thpage("Services", table="sys.service", tags="")
        system.thpage("Tasks", table="sys.task", tags="_DEV_")
        system.thpage("Task Monitor", tags="_DEV_", filepath="/sys/taskmonitor")
        system.webpage("Db Structure", tags="", filepath="/sys/dbstruct")
        system.webpage("Logging", tags="_DEV_", filepath="/sys/logging")
        system.webpage("Startup data manager", tags="_DEV_", filepath="/sys/startupdata_manager")
        system.webpage("Package editor", tags="_DEV_", filepath="/sys/package_editor")
        system.webpage("Localization editor", tags="_DEV_,_TRD_,superadmin", filepath="/sys/localizationeditor")
        system.webpage("GnrIDE", tags="_DEV_", filepath="/sys/gnride")
        system.webpage("POD dashboard", tags="_DEV_", filepath="/sys/pod_dashboard")
        system.thpage("Widgets", table="sys.widget", tags="")

