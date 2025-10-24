import urllib

Bag = 1

class GeoCoderBag(Bag):
    def __init__(self, source=None,api_key=None, **kwargs):
        super().__init__(source, **kwargs)
        self.api_key = api_key
        
    def setGeocode(self, key, address, language='it'):
        """TODO

        :param key: TODO
        :param address: TODO"""
        
        DEBUG = False
        
        urlparams = dict(address=address,sensor='false')
        if language:
            urlparams['language']=language
        if self.api_key:
            urlparams['key'] = self.api_key
        url = "https://maps.googleapis.com/maps/api/geocode/xml?%s" % urllib.parse.urlencode(urlparams)
        self._result = Bag()
        answer = Bag(url)
        if DEBUG:
            print('answer: ', answer)
        if answer['GeocodeResponse.status']=='OK':
            answer=answer['GeocodeResponse.result']
            for n in answer:
                if n.label == 'formatted_address':
                    self._result[n.label]=n.value
                elif n.label == 'address_component':
                    self._parseAddressComponent(n.value)
                elif n.label=='geometry':
                    self._result.setItem('details.geometry',n.value)
        self[key] = self._result
        self.result=None

    def _parseAddressComponent(self, node):
        attr=dict()
        attr[node['type']]=node['long_name']
        self._result['details.%s'%node['type']]=node['short_name']
        self._result.setAttr('formatted_address',**attr)

GeoCoderBagNew = GeoCoderBag #compatibility
