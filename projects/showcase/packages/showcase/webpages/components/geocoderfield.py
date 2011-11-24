# -*- coding: UTF-8 -*-
"""geoCoderField"""

import os
from gnr.core.gnrbag import Bag
import random
import time

cli_max = 12
invoice_max = 20
row_max = 100
sleep_time = 0.05

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"
    
    def test_1_ask(self, pane):
        bc = pane.borderContainer(height='400px')
        right = bc.contentPane(region='right',width='200px',splitter=True)
        center = bc.contentPane(region='center')
        fb = center.formbuilder(cols=2, border_spacing='4px')
        fb.geoCoderField(lbl='Full Address',
                        selected_route='.route',selected_locality='.locality',
                        selected_postal_code='.zip',
                        selectedRecord='.addressbag',
                        colspan=2,width='100%')
        fb.textbox(value='^.route',lbl='Route')
        fb.textbox(value='^.locality',lbl='Locality')
        fb.textbox(value='^.zip',lbl='Zip')
        
        right.tree(storepath='.addressbag',_fired='^.addressbag')
