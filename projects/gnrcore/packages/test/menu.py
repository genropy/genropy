# encoding: utf-8
class Menu(object):
    def config(self,root,**kwargs):
        tests = root.branch(u"!!Tests", tags="_DEV_")
        tests.directoryBranch(u"Batch", folder="batch")
        tests.directoryBranch(u"Components", folder="components")
        tests.directoryBranch(u"Datastore elements", folder="datastore")
        tests.directoryBranch(u"Dojo", folder="dojo")
        tests.directoryBranch(u"Drag & Drop", folder="drag_drop")
        tests.directoryBranch(u"HTML", folder="html")
        tests.directoryBranch(u"Input fields", folder="inputfields")
        tests.directoryBranch(u"Layout", folder="layout")
        tests.directoryBranch(u"Path", folder="path")
        tests.directoryBranch(u"Services", folder="services")
        tests.directoryBranch(u"Tools", folder="tools")
        tests.directoryBranch(u"Websocket", folder="websocket")

