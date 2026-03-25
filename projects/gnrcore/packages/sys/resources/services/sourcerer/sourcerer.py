from gnr.core.gnrbag import Bag
from gnr.lib.services import GnrBaseService
from gnr.core.gnrdecorator import public_method
from gnr.web.gnrbaseclasses import BaseComponent
from gnrpkg.sys.services.sourcerer import SourcererClient


class Service(GnrBaseService):

    def __init__(self, parent=None, url=None, token=None,
                 sourcerer_token=None, **kwargs):
        self.parent = parent
        self.token = token
        self.sourcerer_token = sourcerer_token
        self.client = SourcererClient(url=url, sourcerer_token=sourcerer_token)

    def request_registration(self, host, name, callback_url):
        return self.client.request_registration(host, name, callback_url)

    def check_status(self):
        return self.client.check_status()

    def api_request(self, endpoint, payload=None, method='POST'):
        return self.client.api_request(endpoint, payload, method)


class ServiceParameters(BaseComponent):

    def service_parameters(self, pane, datapath=None, **kwargs):
        fb = pane.formbuilder(datapath=datapath, cols=1, border_spacing='4px')
        fb.textbox(value='^.url', lbl='!!Sourcerer URL',
                   placeholder='https://sourcerer.genropy.net',
                   width='30em')
        fb.textbox(value='^.token', lbl='!!Callback Token',
                   readOnly=True, width='30em')
        fb.textbox(value='^.sourcerer_token', lbl='!!Sourcerer Token',
                   readOnly=True, width='30em')
        fb.button('!![en]Connect to Sourcerer',
                  hidden='^.token').dataRpc(self.rpc_connectToSourcerer,
                   _onResult="""SET .token = result.getItem('token');
                                SET .sourcerer_token = result.getItem('sourcerer_token');
                                this.form.save();""")

    @public_method
    def rpc_connectToSourcerer(self):
        service = self.getService('sourcerer')
        host = self.site.external_host
        callback_url = self.site.externalUrl('/sys/ep_sourcerer')
        site_name = self.site.site_name or host
        result = service.request_registration(host, site_name, callback_url)
        return Bag(result)
