# -*- coding: utf-8 -*-

"""Barcode reader: a textbox that scans a barcode through the camera

`barcodeReaderTextBox` is a textbox with a combo arrow: its tooltip opens a
camera preview, decodes the barcode it sees (`codes` names the reader, here
EAN) and writes the code into the textbox value, playing `sound` on a hit.
The component's preview has a fixed `nodeId`, so a page carries ONE reader.
"""


class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/testhandler:TestHandlerFull,
                     gnrcomponents/barcode_reader/barcode_reader:BarcodeReader"""

    def test_2_tb(self, pane):
        """Open the tooltip and show an EAN barcode to the camera: the last code read appears below

        The controller keeps the code in `.last_barcode` and clears the textbox,
        ready for the next scan.
        """
        fb = pane.formbuilder()
        fb.barcodeReaderTextBox(value='^.barcode', codes="ean", lbl='Barcode',
                                sound='Ping', delay=5)
        fb.div('^.last_barcode', lbl='Last read')
        fb.dataController("""
            SET .last_barcode = barcode;
            SET .barcode = null;
        """, barcode='^.barcode', _if='barcode', _delay=500)
