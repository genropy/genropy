 # -*- coding: utf-8 -*-

# thpage.py
# Created by Francesco Porcari on 2011-05-05.
# Copyright (c) 2011 Softwell. All rights reserved.

class GnrCustomWebPage(object):
    py_requires='gnrcomponents/gnride/gnride'

    def main(self,root,**kwargs):
        root.attributes.update(overflow='hidden')
        root.gnrIdeFrame(datapath='main')
