#!/usr/bin/env pythonw
# -*- coding: utf-8 -*-

from gnr.core.gnrlang import GnrException
from gnr.lib import logger
from gnr.lib.services.storage import StorageService
from gnr.web.gnrbaseclasses import BaseComponent

#implementations whose base_path is not a real path: they cannot be the parent
#of a relative service because their paths are resolved by service name
UNSUPPORTED_PARENT_IMPLEMENTATIONS = ('symbolic', 'http')

RELATIVE_SERVICE_CLASSES = {}


def relativeServiceClass(parent_service):
    """Returns the class of a relative service built over a parent storage service.

    A relative service must behave exactly as its parent implementation, so its class
    is created (and cached) as a subclass of the parent service class: Service comes
    first in the mro, so it only overrides the base path, while every other method is
    the one of the parent implementation.

    :param parent_service: the parent storage service instance"""
    parent_class = parent_service.__class__
    if issubclass(parent_class, Service):
        #the parent is a relative service itself: its class is already the right one
        return parent_class
    relative_class = RELATIVE_SERVICE_CLASSES.get(parent_class)
    if relative_class is None:
        implementation = getattr(parent_service, 'service_implementation', None)
        relative_class = type('Relative_%s' % (implementation or parent_class.__name__),
                              (Service, parent_class), {})
        RELATIVE_SERVICE_CLASSES[parent_class] = relative_class
    return relative_class


class Service(StorageService):
    """Storage service rooted on a subpath of another storage service.

    Only the parent service and the relative path are configured: implementation and
    parameters (base path, bucket, credentials...) are the ones of the parent service,
    so a subfolder of an existing storage can be published as a service of its own
    without repeating any parameter."""

    def __init__(self, parent=None, relative_path=None, parent_service=None, **kwargs):
        self.parent = parent
        self.parent_service_name = parent_service
        self.relative_path = (relative_path or '').strip('/')
        self.parent_service = self._resolveParentService(parent_service)
        if self.parent_service is None:
            #not configured yet: the service is browsable (and empty) but not writable,
            #so that the form where it gets configured does not fail on it
            self.__class__ = UnconfiguredService
        else:
            self.__class__ = relativeServiceClass(self.parent_service)

    def _resolveParentService(self, parent_service):
        """Returns the parent storage service, None if it is missing or unusable"""
        if not parent_service:
            logger.warning('Relative storage service without parent service')
            return None
        service = self.parent.storage(parent_service)
        implementation = getattr(service, 'service_implementation', None)
        if implementation in UNSUPPORTED_PARENT_IMPLEMENTATIONS:
            logger.warning('Storage service %s cannot be the parent of a relative service',
                           parent_service)
            return None
        return service

    @property
    def base_path(self):
        parent_base_path = self.parent_service.base_path
        if not parent_base_path:
            return self.relative_path
        if not self.relative_path:
            return parent_base_path
        return '%s/%s' % (parent_base_path.rstrip('/'), self.relative_path)

    def __getattr__(self, name):
        """Every parameter not owned by the relative service is the one of its parent"""
        parent_service = self.__dict__.get('parent_service')
        if parent_service is None:
            raise AttributeError(name)
        return getattr(parent_service, name)


class UnconfiguredService(StorageService):
    """A relative storage service whose parent service is missing or unusable.

    It behaves as an empty storage, so that listing it (the service parameters form
    shows its tree) does not fail, and refuses any operation on its content: nothing
    can be written where there is no path yet."""

    @property
    def base_path(self):
        return None

    def internal_path(self, *args, **kwargs):
        return None

    def exists(self, *args):
        return False

    def isdir(self, *args):
        return False

    def isfile(self, *args):
        return False

    def children(self, *args, **kwargs):
        return []

    def url(self, *args, **kwargs):
        return ''

    def open(self, *args, **kwargs):
        raise GnrException(self._unconfigured_message)

    def local_path(self, *args, **kwargs):
        raise GnrException(self._unconfigured_message)

    def mkdir(self, *args, **kwargs):
        raise GnrException(self._unconfigured_message)

    def makedirs(self, *args, **kwargs):
        raise GnrException(self._unconfigured_message)

    @property
    def _unconfigured_message(self):
        return 'Storage service %s has no usable parent service: set it in the service parameters' % self.service_name


class ServiceParameters(BaseComponent):
    py_requires = 'gnrcomponents/storagetree:StorageTree'

    def service_parameters(self, pane, datapath=None, service_name=None, **kwargs):
        bc = pane.borderContainer()
        fb = bc.contentPane(region='top').formbuilder(datapath=datapath)
        fb.filteringSelect(value='^.parent_service', lbl='!!Parent service', hasDownArrow=True,
                           values=self.relativeStorageParents(service_name=service_name))
        fb.textbox(value='^.relative_path', lbl='!!Relative path')
        bc.storageTreeFrame(frameCode='relativeStorage', storagepath='^#FORM.record.service_name?=#v+":"',
                                border='1px solid silver', margin='2px', rounded=4,
                                region='center', preview_region='right',
                                store__onBuilt=True,
                                preview_border_left='1px solid silver', preview_width='50%')

    def relativeStorageParents(self, service_name=None):
        """Returns the storage services usable as parent of a relative service"""
        storage_params = self.site.storage_handler.getAllStorageParameters()
        names = set([name for name, params in storage_params.items()
                     if name != service_name and not name.startswith('_')
                     and params.get('implementation') not in UNSUPPORTED_PARENT_IMPLEMENTATIONS])
        #the configured parent is always an option, even if it is not available any more
        current_parent = (storage_params.get(service_name) or {}).get('parent_service')
        if current_parent:
            names.add(current_parent)
        return ','.join(sorted(names))
