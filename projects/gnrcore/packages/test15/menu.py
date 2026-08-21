# encoding: utf-8
class Menu(object):
    def config(self,root,**kwargs):
        tests = root.branch(u"!!Tests", tags="_DEV_")
        tests.branch(u"Tools", tags="", pkg="test15", dir="tools")

