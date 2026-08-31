from gnrpkg.sys.services.dnsmanager import DnsManager
from gnr.utils.awsmanager import AWSManager
from gnr.web.gnrbaseclasses import BaseComponent
from gnr.core.gnrdecorator import public_method

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
        fb.textbox(value='^.aws_access_key_id', lbl='Aws Access Key Id')
        fb.textbox(value='^.aws_secret_access_key', lbl='Aws Secret Access Key')
        center = bc.contentPane(region='center', padding='8px')

        cfb = center.formbuilder(cols=1)
        cfb.button('List Hosted Zones').dataRpc(
            self.r53_list_hosted_zones,
            service_name='=#FORM.record.service_name',
            _if='service_name'
        ).addCallback('genro.dlg.alert(result,"Hosted Zones")')
        
        cfb.button('Check Record Exists').dataRpc(
            self.r53_check_record_exists,
            service_name='=#FORM.record.service_name',
            _if='service_name',
            _ask=dict(title='Check Record Exists', fields=[
                dict(name='name', lbl='Record Name'),
                dict(name='hosted_zone_id', lbl='Hosted Zone ID (optional)')
            ])
        ).addCallback('genro.dlg.alert(result,"Record Exists")')
        
        cfb.button('Verify Record').dataRpc(
            self.r53_verify_record,
            service_name='=#FORM.record.service_name',
            _if='service_name',
            _ask=dict(title='Verify DNS Record', fields=[
                dict(name='name', lbl='Record Name'),
                dict(name='record_type', lbl='Record Type (A, CNAME, MX, ...)'),
                dict(name='value', lbl='Expected Value'),
                dict(name='hosted_zone_id', lbl='Hosted Zone ID (optional)')
            ])
        ).addCallback('genro.dlg.alert(result,"Verify Record")')

    @public_method
    def r53_list_hosted_zones(self, service_name=None, **kwargs):
        service = self.getService('dnsmanager', service_name)
        zones = service.get_hosted_zones()
        if not zones:
            return 'No hosted zones found.'
        return '\n'.join('%s  (%s)' % (name, zone_id) for name, zone_id in zones.items())

    @public_method
    def r53_check_record_exists(self, service_name=None, name=None, hosted_zone_id=None, **kwargs):
        service = self.getService('dnsmanager', service_name)
        result = service.record_exists(name=name, hosted_zone_id=hosted_zone_id or None)
        if result['status'] == 'ok':
            return 'Record "%s" EXISTS in Route53.' % name
        return '%s: "%s".' % (result['description'], name)

    @public_method
    def r53_verify_record(self, service_name=None, name=None, record_type=None,
                          value=None, hosted_zone_id=None, **kwargs):
        service = self.getService('dnsmanager', service_name)
        result = service.verify_record(name=name, record_type=record_type,
                                       value=value, hosted_zone_id=hosted_zone_id or None)
        if result['status'] == 'ok':
            return 'Record "%s" (%s) matches expected value "%s".' % (name, record_type, value)
        return '%s: "%s" (%s).' % (result['description'], name, record_type)
