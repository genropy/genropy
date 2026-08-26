from gnrpkg.sys.services.dnsmanager import DnsManager
from gnr.utils.awsmanager import AWSManager
from gnr.web.gnrbaseclasses import BaseComponent

class Service(DnsManager):

    def __init__(self, parent,
                 aws_access_key_id=None,
                 aws_secret_access_key=None):
        self.parent=parent
        self.aws_manager = AWSManager(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key)

    def get_hosted_zones(self):
        return self.aws_manager.Route53.get_hosted_zones()

    def record_exists(self, name, hosted_zone_id=None):
        return self.aws_manager.Route53.record_exists(name=name, hosted_zone_id=hosted_zone_id)

    def verify_record(self, name, record_type, value, hosted_zone_id=None):
        return self.aws_manager.Route53.verify_record(name=name, record_type=record_type,
            value=value, hosted_zone_id=hosted_zone_id)

    def ensure_cname_record(self, name, value, ttl=300, dryrun=False):
        return self.aws_manager.Route53.ensure_cname_record(name=name, value=value,
            ttl=ttl, dryrun=dryrun)


class ServiceParameters(BaseComponent):
    def service_parameters(self, pane, datapath=None, **kwargs):
        bc = pane.borderContainer()
        fb = bc.contentPane(region='top').formbuilder(datapath=datapath)
        fb.textbox(value='^.aws_access_key_id',lbl='Aws Access Key Id')
        fb.textbox(value='^.aws_secret_access_key',lbl='Aws Secret Access Key')
