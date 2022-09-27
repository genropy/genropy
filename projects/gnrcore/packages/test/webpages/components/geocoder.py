# -*- coding: utf-8 -*-

"Geocoder"

from gnr.core.gnrbag import Bag

class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def windowTitle(self):
        return 'GeocoderField Test'

    def test_0_geocoder_with_map(self, pane):
        """Please set your Google Maps API credentials in instanceconfig.xml before using (see documentation).
        Geocoder searches for full address to set parameters, in this case showing a map."""
        bc=pane.borderContainer(margin='5px', height='250px')
        top =bc.contentPane(region='left', width='50%', margin='5px')
        fb = top.formbuilder(cols=1,lbl_font_weight='bold', lbl_color='^.lblcolor',
                                                 fld_width='100%', colswidth='auto',
                                                 margin='5px')
    
        fb.geoCoderField(value='^.geodesc',
                        width='100%',
                        lbl='Full Address',
                        selected_street_address='.street_address',
                        selected_locality='.locality',
                        selected_administrative_area_level_2='.state',
                        selected_postal_code='.zip',
                        selected_position='.geocoder')
        fb.textbox(value='^.street_address',lbl='Route')
        fb.textbox(value='^.locality',lbl='Locality')
        fb.textbox(value='^.state',lbl='State')
        fb.textbox(value='^.zip',lbl='Zip')
        center=bc.contentPane(region='center', margin='5px')
        center.GoogleMap(height='200px', 
                     map_center="^.geocoder",
                     map_type='roadmap',
                     map_zoom=15,
                     centerMarker=True,
                     map_disableDefaultUI=True)

    def test_1_ask(self, pane):
        "Same as before, but instead of showing map it shows a tree with all available fields"
        bc = pane.borderContainer(height='250px')
        right = bc.contentPane(region='right',width='250px',splitter=True)
        center = bc.contentPane(region='center')
        fb = center.formbuilder(cols=2, border_spacing='4px')
        fb.geoCoderField(lbl='Full Address',
                        selected_street_address='.street_address',selected_locality='.locality',
                        selected_postal_code='.zip',
                        selectedRecord='.addressbag',
                        colspan=2,width='100%')
        fb.textbox(value='^.street_address',lbl='Route')
        fb.textbox(value='^.locality',lbl='Locality')
        fb.textbox(value='^.zip',lbl='Zip')
        
        right.tree(storepath='.addressbag',_fired='^.addressbag')

    def test_2_w3w(self,pane):
        """Please set your W3W API credentials in instanceconfig.xml before using (see documentation).
        W3W is a service which allows to find a location with a unique combination of 3 words. Enjoy!"""
        bc = pane.borderContainer(height='600px',width='800px')
        top = bc.contentPane(region='top',padding='10px')
        fb = top.formbuilder()
        fb.geoCoderField(value='^.fulladdress',lbl='Full Address',country='IT',
                       selected_position='.geocoords',
                       selected_w3w='.w3w',
                       width='30em')
        fb.div('^.geocoords',lbl='Coords')
        fb.div('^.w3w.words',lbl='W3W')
        center = bc.contentPane(region='center')
        
        m = center.GoogleMap(height='100%', width='100%',
                    map_event_bounds_changed="""genro.w3w.drawGrid(this,$1)""",
                    map_type='satellite',
                    map_center='^.geocoords',
                    nodeId='gma',
                    w3w='.w3w',
                    centerMarker=dict(title='', label='X',draggable=True,
                                       event_dragend="genro.w3w.setCurrentW3W(this,$1);"),
                    autoFit=True)
        bc.dataFormula('.w3w',"genro.w3w.convertTo3wa(geocoords)",geocoords='^.geocoords')
        bc.dataController('sn.markers.center_marker.setTitle(w3w_words)',
                        w3w_words='^.w3w.words',sn=m,_delay=500)

        