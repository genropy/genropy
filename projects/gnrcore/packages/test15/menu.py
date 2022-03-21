# encoding: utf-8
class Menu(object):
    def config(self,root,**kwargs):
        tests = root.branch(u"!!Tests", tags="_DEV_")
        tests.branch(u"Components", tags="", pkg="test15", dir="components")
        tests.branch(u"Dojo", tags="", pkg="test15", dir="dojo")
        tests.branch(u"Gnrwdg", tags="", pkg="test15", dir="gnrwdg")
        tests.branch(u"Dev tools", tags="", pkg="test15", dir="devtools")
        tests.branch(u"Tools", tags="", pkg="test15", dir="tools")

