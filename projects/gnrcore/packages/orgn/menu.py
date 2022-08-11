# encoding: utf-8
class Menu(object):
    def config(self,root,**kwargs):
        organizer = root.branch(u"!!Organizer", tags="admin")
        organizer.thpage(u"!!Annotations", table="orgn.annotation", tags="")
        organizer.thpage(u"!!Action types", table="orgn.action_type", tags="")
        organizer.thpage(u"!!Annotation types", table="orgn.annotation_type", tags="")

