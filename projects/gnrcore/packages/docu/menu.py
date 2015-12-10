#!/usr/bin/python
# -*- coding: UTF-8 -*-

def config(root,application=None):
    docu = root.branch('Documentation')
    docu.thpage('!!Documentation',table='docu.documentation')
    docu.lookups(u"!!Docu tables", lookup_manager="docu")
