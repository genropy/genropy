from suds.client import Client
from past.builtins import basestring
from gnr.core.gnrbag import Bag
from suds.client import Client

ENV_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
                   <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                    <soap:Body>
                        {xml_body}
                     </soap:Body>
                    </soap:Envelope>"""
                    
class GnrSudsClient(object):
    
    def __init__(self, server_url=None, timeout=None, **kwargs):
        self.wsdl_url = '{server_url}?wsdl'.format(server_url=server_url)
        self.timeout = timeout
        self.parameters = kwargs
        self.client = Client(self.wsdl_url)
        if self.timeout:
            self.client.set_options(timeout=self.timeout)

    def _prepareEnvelope(self, method=None, **kwargs):
        call_bag = Bag(kwargs)
        xml_body =  Bag({method:call_bag}).toXml(docHeader=False, omitRoot=True, typeattrs=False, typevalue=False)
        xml_envelope = ENV_TEMPLATE.format(xml_body=xml_body)
        return dict(msg=xml_envelope)


    def __call__(self, method=None, **kwargs):
        service_handler = getattr(self.client.service, method, None)
        if service_handler:
            try:
                r = service_handler(__inject=self._prepareEnvelope(method=method, **kwargs))
                result = self._sudsToBag(r.RESULT)
            except Exception as e:
                result = Bag(dict(success=False, error=str(e), statuscode='SOAP ERROR'))
            return result
        
    def _sudsToBag(self, item):
        result = Bag()
        k_list = getattr(item,'__keylist__',None)
        if k_list:
            for k in k_list:
                v = getattr(item,k,None)
                result.addItem(k, self._sudsToBag(v))
        elif isinstance(item,basestring):
            result = str(item)
        elif isinstance(item, list):
            for j,s in enumerate(item):
                result['r_%s' % j]=self._sudsToBag(s)
        return result


#if __name__ == 'main':
#    url = 'http://www.damasystem.net/WsGestioneServiziOnl/WsPrenotazioneServizio.asmx'
#    cliente = '09809000'
#    username = 'WT09000'
#    password = 'REVTST22_!'
#    c = GnrSudsClient(server_url=url, cliente=cliente, username=username, password=password)