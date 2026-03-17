import os
import os.path
import glob

from gnr.core.gnrbag import Bag
from gnr.core.gnrlang import GnrException
from gnr.core.gnrsys import expandpath
from gnr.core.gnrconfig import getGnrConfig, setEnvironment

class UnknownEntityTypeException(GnrException):
    pass

class EntityNotFoundException(GnrException):
    pass


class PathResolver(object):
    """TODO"""
    entities = dict(
            instance='instances',
            site='sites',
            resource='resources',
            package='packages',
            project='projects')
            
    def __init__(self, gnr_config=None):
        self.gnr_config = gnr_config or getGnrConfig()
        setEnvironment(self.gnr_config)
                
    def js_path(self, lib_type='gnr', version='11'):
        """TODO Return the configuration static js path, with *lib_type* and *version* specified
        
        :param lib_type: Genro Javascript library == gnr
        :param version: the Genro Javascript library version related to the Dojo one. The number of Dojo
                        version is written without any dot. E.g: '11' is in place of '1.1'"""
        path = self.gnr_config['gnr.environment_xml.static.js.%s_%s?path' % (lib_type, version)]
        if path:
            path = os.path.join(expandpath(path), 'js')
        return path
        
    def entity_name_to_path(self, entity_name, entity_type, look_in_projects=True):
        """Resolve an entity type to a local path where to retrieve the requested object,
        veryfing the existance of the entity itself.
        
        :param entity_name: the entity name
        :param entity_type: the entity type, a predefined list
        :param look_in_projects: TODO"""
        entity = self.entities.get(entity_type)
        if not entity:
            raise UnknownEntityTypeException('Error: entity type %s not known' % entity_type)
        if entity in self.gnr_config['gnr.environment_xml']:
            for path in [expandpath(path) for path in
                         self.gnr_config['gnr.environment_xml'].digest('%s:#a.path' % entity) if
                         os.path.isdir(expandpath(path))]:
                entity_path = os.path.join(path, entity_name)
                if os.path.isdir(entity_path):
                    return expandpath(entity_path)
        if look_in_projects and 'projects' in self.gnr_config['gnr.environment_xml']:
            projects = [expandpath(path) for path in self.gnr_config['gnr.environment_xml'].digest('projects:#a.path')
                        if os.path.isdir(expandpath(path))]
            local_projects = os.environ.get('GNR_LOCAL_PROJECTS')
            if local_projects:
                projects = [expandpath(local_projects) ]+projects
            for project_path in projects:
                folders = glob.glob(os.path.join(project_path, '*',entity,entity_name))
                if folders:
                    return expandpath(folders[0])
                elif entity_type=='site':
                    folders = glob.glob(os.path.join(project_path, '*','instances',entity_name))
                    if folders:
                        sitepath = expandpath(os.path.join(folders[0],'site'))
                        root_py_path = expandpath(os.path.join(folders[0],'root.py'))
                        if os.path.exists(root_py_path):
                            if not os.path.exists(sitepath):
                                os.makedirs(sitepath, exist_ok=True)
                            return sitepath

                        
        raise EntityNotFoundException('Error: %s %s not found' % (entity_type, entity_name))
        
    def site_name_to_path(self, site_name):
        """TODO
        
        :param site_name: TODO"""
        return self.entity_name_to_path(site_name, 'site')
    
    def get_instanceconfig(self, instance_name):
        instanceFolder = self.instance_name_to_path(instance_name)
        project_packages_path = os.path.normpath(os.path.join(instanceFolder, '..', '..', 'packages'))
        if os.path.isdir(project_packages_path):
            project_packages_path = project_packages_path
        if os.path.exists(os.path.join(instanceFolder,'config','instanceconfig.xml')):
            instanceFolder = os.path.join(instanceFolder,'config')
        
        if not instanceFolder:
            return Bag()

        def normalizePackages(config):
            if config['packages']:
                packages = Bag()
                for n in config['packages']:
                    packages.setItem(n.attr.get('pkgcode') or n.label, n.value, n.attr)
                config['packages']  = packages
            return config
        instance_config_path = os.path.join(instanceFolder, 'instanceconfig.xml')
        base_instance_config = normalizePackages(Bag(instance_config_path))
        instance_config = normalizePackages(self.gnr_config['gnr.instanceconfig.default_xml']) or Bag()
        template = base_instance_config['instance?template']
        if template:
            template_update = self.gnr_config['gnr.instanceconfig.%s_xml' % template]
            if template_update:
                instance_config.update(normalizePackages(template_update) or Bag())
            else:
                template_config_path = os.path.join(self.instance_name_to_path(template),'config','instanceconfig.xml')
                if os.path.exists(template_config_path):
                    instance_config.update(normalizePackages(Bag(template_config_path)) or Bag())
                
        if 'instances' in self.gnr_config['gnr.environment_xml']:
            for path, instance_template in self.gnr_config.digest(
                    'gnr.environment_xml.instances:#a.path,#a.instance_template') or []:
                if path == os.path.dirname(instanceFolder):
                    instance_config.update(normalizePackages(self.gnr_config['gnr.instanceconfig.%s_xml' % instance_template]) or Bag())
        instance_config.update(base_instance_config)
        return instance_config


    def get_siteconfig(self,site_name):
        site_config = self.gnr_config['gnr.siteconfig.default_xml']
        site_config_path = self.site_name_to_config_path(site_name)
        path_list = []
        if 'projects' in self.gnr_config['gnr.environment_xml']:
            projects = [(expandpath(path), site_template) for path, site_template in
                        self.gnr_config['gnr.environment_xml.projects'].digest('#a.path,#a.site_template') if
                        os.path.isdir(expandpath(path))]
            for project_path, site_template in projects:
                sites = glob.glob(os.path.join(project_path, '*/sites'))
                path_list.extend([(site_path, site_template) for site_path in sites])
            for path, site_template in path_list:
                if path == site_name:
                    if site_config:
                        site_config.update(self.gnr_config['gnr.siteconfig.%s_xml' % site_template] or Bag())
                    else:
                        site_config = self.gnr_config['gnr.siteconfig.%s_xml' % site_template]
        if site_config:
            site_config.update(Bag(site_config_path))
        else:
            site_config = Bag(site_config_path)

        # siteconfig can be update from the contents of the <site/>
        # tag inside an instanceconfig.xml 
        instance_config = self.get_instanceconfig(site_name)
        if instance_config and instance_config['site']:
            site_config.update(instance_config['site'])
            
        return site_config


    def site_name_to_config_path(self,site_name):
        site_path = self.site_name_to_path(site_name)
        site_config_path = os.path.join(site_path,'siteconfig.xml')
        if os.path.exists(site_config_path):
            return site_config_path
        site_config_path = os.path.join(self.instance_name_to_path(site_name),'config','siteconfig.xml')
        if os.path.exists(site_config_path):
            return site_config_path

    def instance_name_to_path(self, instance_name):
        """TODO
        
        :param instance_name: TODO"""
        return self.entity_name_to_path(instance_name, 'instance')
        
    def package_name_to_path(self, package_name):
        """TODO
        
        :param package_name: TODO"""
        return self.entity_name_to_path(package_name, 'package')
        
    def resource_name_to_path(self, resource_name):
        """TODO
        
        :param resource_name: TODO"""
        return self.entity_name_to_path(resource_name, 'resource')
        
    def project_name_to_path(self, project_name):
        """TODO
        
        :param project_name: TODO"""
        return self.entity_name_to_path(project_name, 'project', look_in_projects=False)
        
    def project_repository_name_to_path(self, project_repository_name, strict=True):
        """TODO
        
        :param project_repository_name: TODO
        :param strict: TODO"""
        if not strict or 'gnr.environment_xml.projects.%s' % project_repository_name in self.gnr_config:
            path = self.gnr_config['gnr.environment_xml.projects.%s?path' % project_repository_name]
            if path:
                return expandpath(path)
        else:
            raise EntityNotFoundException('Error: Project Repository %s not found' % project_repository_name)
