# -*- coding: utf-8 -*-

"""Moveable div reporting its own position through the datastore

The yellow square is created with moveable=True and its top/left are bound to
the `ob` datastore node, so dragging it writes the new coordinates back and the
two divs inside it display them live. This is the client-side half of the
collaborative drawing surface: sharing the coordinates between browsers needs
the shared datastore of `collaborative.py`.
"""

from gnr.core.gnrbag import Bag

class GnrCustomWebPage(object):
    
    def isDeveloper(self):
        return True

    def main(self,root,room=None,**kwargs):
        bc = root.borderContainer(datapath='main')
        top = bc.contentPane(region='top')
        top.data('ob',Bag(dict(top='100px',left='100px')))
        fb = top.div(padding='10px').formbuilder(cols=2,border_spacing='3px',datapath='.shared.info')
        fb.button('make',action='')
        center=bc.contentPane(region='center')

        m=center.div(position='absolute',border='1px solid red',
                         top='^ob.top',width='100px',height='100px',left='^ob.left',
                             background='yellow',moveable=True)
        m.div('^ob.top')
        m.div('^ob.left')
