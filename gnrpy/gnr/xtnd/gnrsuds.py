from suds.client import Client
from gnr.core.gnrbag import Bag
from suds.client import Client
from suds import byte_str


class GnrSudsClient(object):
    
    def __init__(self, server_url=None, timeout=None, xmlns=None, envelope_template=None, request_tag=None, **kwargs):
        self.wsdl_url = '{server_url}?wsdl'.format(server_url=server_url)
        self.timeout = timeout
        self.parameters = kwargs
        self.xmlns = xmlns
        self.request_tag = request_tag
        self.envelope_template = envelope_template
        self.client = Client(self.wsdl_url)
        if self.timeout:
            self.client.set_options(timeout=self.timeout)

    def _prepareEnvelope(self, method=None, **kwargs):
        parameters_bag = Bag(kwargs)
        if self.request_tag:
            request_tag = self.request_tag
        else:
            request_tag = method
        call_bag = Bag({request_tag:parameters_bag})
        if self.xmlns:
            call_bag.setAttr(request_tag, xmlns=self.xmlns)
        xml_body =  call_bag.toXml(docHeader=False, omitRoot=True, typeattrs=False, typevalue=False)
        xml_envelope = self.envelope_template.format(xml_body=xml_body).replace('\n','').replace('\t','')
        
        xml_envelope = byte_str(xml_envelope)
        return dict(msg=xml_envelope)

    def service_handler(self, method):
        return getattr(self.client.service, method, None)
        
    def __call__(self, method=None, **kwargs):
        service_handler = self.service_handler(method)
        if service_handler:
            if True:
                envelope = self._prepareEnvelope(method=method, **kwargs)
                r = service_handler(__inject=envelope)
                answer = Bag(success=True, result=r, envelope=envelope['msg'], statuscode=r)
            #except Exception as e:
            #    answer = Bag(dict(success=False, result=None, error=str(e), statuscode='SOAP ERROR',envelope=envelope['msg']))
        else:
            answer = Bag(dict(success=False, result=None, statuscode='METHOD NOT FOUND'))
        return answer
