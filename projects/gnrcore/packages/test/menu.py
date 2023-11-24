# encoding: utf-8
class Menu(object):
    def config(self,root,**kwargs):
        tests = root.branch("!!Tests", tags="_DEV_")
        tests.directoryBranch("Batch", folder="batch")
        tests.directoryBranch("Components", folder="components")
        tests.directoryBranch("Datastore elements", folder="datastore")
        tests.directoryBranch("Dojo", folder="dojo")
        tests.directoryBranch("Google", folder="google")
        tests.directoryBranch("Drag & Drop", folder="drag_drop")
        tests.directoryBranch("Gnr widgets", folder="gnrwdg")
        tests.directoryBranch("HTML", folder="html")
        tests.directoryBranch("Input fields", folder="inputfields")
        tests.directoryBranch("Layout", folder="layout")
        tests.directoryBranch("Path", folder="path")
        tests.directoryBranch("Services", folder="services")
        tests.directoryBranch("Tools", folder="tools")
        tests.directoryBranch("Websocket", folder="websocket")

