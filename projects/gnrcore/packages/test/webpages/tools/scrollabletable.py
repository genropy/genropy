# -*- coding: utf-8 -*-

"Shortcuts"

class GnrCustomWebPage(object):
    py_requires="gnrcomponents/testhandler:TestHandlerBase"

    def test_0_json(self,pane):
        bc = pane.borderContainer(height='300px',width='400px',border='1px solid silver')
        box = pane.div(height='300px',width='400px',border='1px solid silver')
        pane.button('Load').dataController("""
                                           let kw = {};
                                            kw.cols = struct;
                                           box.domNode.innerHTML = genro.dom.jsonTable(source,kw);
                                           """,
            box=box,
            source = [{'prodotto':'Uova','quantita':3,'prezzo':1.2},
                      {'prodotto':'Mele','quantita':6,'prezzo':4},
                      {'prodotto':'Banane','quantita':1,'prezzo':0.5},
                      {'prodotto':'Kiwi','quantita':3,'prezzo':1.2},
                      {'prodotto':'Lime','quantita':6,'prezzo':4},
                      {'prodotto':'Cachi','quantita':1,'prezzo':0.5}],
            struct = [
                dict(field='prodotto',name='Prodotto'),
                dict(field='quantita',name='Qt',dtype='N',format='#,###.00'),
                dict(field='prezzo',name='Prezzo',dtype='N',format='#,###.00')
            ]
        )