# encoding: utf-8
def config(root,application=None):
    test = root.branch(u"!!Tests", tags="_DEV_",)
    test.branch("Components", pkg="test", dir='components')
    test.branch("Controllers", pkg="test", dir='controllers')
    test.branch("Drag & Drop", pkg="test", dir='drag_drop')
    test.branch("HTML", pkg="test", dir='html')
    test.branch("Services", pkg="test", dir='services')
#    test.branch("Dojo" , pkg="test", dir='dojo')
#    test.branch("Gnrwdg", pkg="test", dir='gnrwdg')
#    test.branch("Dev tools", pkg="test", dir='devtools')
#    test.branch("Tools", pkg="test", dir='tools')