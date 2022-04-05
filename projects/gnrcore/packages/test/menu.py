# encoding: utf-8
class Menu(object):
    def config(self,root,**kwargs):
        tests = root.branch(u"!!Tests", tags="_DEV_")
        tests.webpage(u"Batch", folder="batch")
        tests.webpage(u"Components", folder="components")
        tests.webpage(u"Datastore elements", folder="datastore")
        tests.webpage(u"Dojo", folder="dojo")
        tests.webpage(u"Drag & Drop", folder="drag_drop")
        tests.webpage(u"HTML", folder="html")
        tests.webpage(u"Input fields", folder="inputfields")
        tests.webpage(u"Layout", folder="layout")
        tests.webpage(u"Path", folder="path")
        tests.webpage(u"Services", folder="services")
        tests.webpage(u"Tools", folder="tools")
        tests.webpage(u"Websocket", folder="websocket")

