# encoding: utf-8
def config(root,application=None):
    test = root.branch(u"!!Tests", tags="_DEV_")
    test.branch("Components", pkg="test", dir='components')
    test.branch("Datastore elements", pkg="test", dir='datastore')
    test.branch("Dojo", pkg="test", dir='dojo')
    test.branch("Drag & Drop", pkg="test", dir='drag_drop')
    test.branch("HTML", pkg="test", dir='html')
    test.branch("Input fields", pkg="test", dir='inputfields')
    test.branch("Layout", pkg="test", dir='layout')
    test.branch("Path", pkg="test", dir='path')
    test.branch("Services", pkg="test", dir='services')
    test.branch("Websocket", pkg="test", dir='websocket')