from gnrpkg.sys.services.cloudmanager import CloudManager
from gnr.utils.awsmanager import AWSManager
from gnr.web.gnrbaseclasses import BaseComponent

class Service(CloudManager):

    def __init__(self, parent, aws_access_key_id=None,
        aws_secret_access_key=None,
        region_name=None):
        self.parent=parent
        self.aws_manager = AWSManager(aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name)

    def regions(self, service_name=None, region_name=None):
        return self.aws_manager.regions(service_name=service_name, region_name=region_name)

    def get_instances(self):
        return self.aws_manager.EC2.get_instances()

    def create_user(self, username=None):
        return self.aws_manager.IAM.create_user(username=username)

    def delete_user(self, username=None):
        return self.aws_manager.IAM.delete_user(username=username)

    def get_user(self, username=None):
        return self.aws_manager.IAM.get_user(username=username)

    def put_user_policy(self, username=None, policyname=None, policydocument=None):
        return self.aws_manager.IAM.put_user_policy(username=username, policyname=policyname,
            policydocument=policydocument)

    def get_usernames(self):
        return self.aws_manager.IAM.get_usernames()

    def create_user_key_pair(self, username=None):
        return self.aws_manager.IAM.create_user_key_pair(username=username)

    def get_s3_policy(self, bucket=None, folder=None):
        return self.aws_manager.S3.get_s3_policy(bucket=bucket, folder=folder)

    def get_sqs_policy(self, queue_name=None, full_access=None):
        return self.aws_manager.SQS.get_sqs_policy(queue_name=queue_name, full_access=full_access)

    def allow_sqs_queue_for_user(self, username=None, queue_name=None, full_access=None):
        policy = self.get_sqs_policy(queue_name=queue_name, full_access=full_access)
        self.put_user_policy(username=username, policyname='sqs_policy_%s_%s'%(username, queue_name),
            policydocument=policy)

    def create_s3_for_user(self, username=None, bucket=None, region=None):
        return self.aws_manager.S3.create_s3_for_user(username=username,
            bucket=bucket, region=region)

    def allow_s3_folder_for_user(self, username=None, bucket=None, folder=None):
        return self.aws_manager.S3.allow_s3_folder_for_user(username=username,
            bucket=bucket, folder=folder)

    def get_hosted_zones(self):
        return self.aws_manager.Route53.get_hosted_zones()

    # ECS Methods
    def list_ecs_clusters(self):
        return self.aws_manager.ECS.list_clusters()

    def list_ecs_services(self, cluster):
        return self.aws_manager.ECS.list_services(cluster=cluster)

    def list_ecs_tasks(self, cluster, service=None):
        return self.aws_manager.ECS.list_tasks(cluster=cluster, service=service)

    def force_update_ecs_service(self, cluster, service):
        return self.aws_manager.ECS.force_update_service(cluster=cluster, service=service)

    # RDS Methods
    def list_rds_instances(self):
        return self.aws_manager.RDS.list_instances()
    
    # Secrets Manager Methods
    def create_secret(self, name, secret_value, description=None, tags=None):
        return self.aws_manager.SecretsManager.create_secret(name=name, secret_value=secret_value, 
                                                          description=description, tags=tags)

    def get_secret_value(self, secret_id, version_id=None, version_stage=None):
        return self.aws_manager.SecretsManager.get_secret_value(secret_id=secret_id,
                                                             version_id=version_id,
                                                             version_stage=version_stage)

    def update_secret(self, secret_id, secret_value, description=None):
        return self.aws_manager.SecretsManager.update_secret(secret_id=secret_id,
                                                          secret_value=secret_value,
                                                          description=description)

    def delete_secret(self, secret_id, force_delete=False, recovery_window_days=30):
        return self.aws_manager.SecretsManager.delete_secret(secret_id=secret_id,
                                                          force_delete=force_delete,
                                                          recovery_window_days=recovery_window_days)

    def list_secrets(self, filters=None, max_results=100):
        return self.aws_manager.SecretsManager.list_secrets(filters=filters,
                                                         max_results=max_results)

class ServiceParameters(BaseComponent):
    def service_parameters(self,pane,datapath=None,**kwargs):
        fb = pane.formbuilder(datapath=datapath)
        fb.textbox(value='^.aws_access_key_id',lbl='Aws Access Key Id')
        fb.textbox(value='^.aws_secret_access_key',lbl='Aws Secret Access Key')
        fb.textbox(value='^.region_name',lbl='Region Name')
