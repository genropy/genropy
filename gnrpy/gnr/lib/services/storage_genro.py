#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Storage service backed by genro-storage.

A StorageService whose operations run through a genro_storage StorageManager
mount instead of os/boto3. The legacy StorageNode sits unchanged on top of it,
so path parsing, base64, internal_url, listdir, autocreate, copy and move keep
coming from StorageService and behave as they do on the legacy services.
"""

import os
import shutil

from genro_storage.exceptions import StorageError

from gnr.core.gnrsys import expandpath
from gnr.lib.services.storage import (LocalPath, StorageNode, StorageService,
                                      _SimpleFileApp)

GNRDIR_SENTINEL = '.gnrdir'


class Service(StorageService):
    """Serves one genro-storage mount through the legacy StorageService API.

    Args:
        parent: the site
        manager: the genro_storage StorageManager holding the mount
        mount_name: name of the mount in that manager
        mount_config: the configuration dict the mount was registered with
        expand_paths: expand '~' in incoming paths (the legacy 'raw' behaviour)
        versioned: False disables versioning on a backend that supports it,
                as the legacy aws_s3 service's own versioned parameter does
    """

    def __init__(self, parent=None, manager=None, mount_name=None,
                 mount_config=None, expand_paths=False, versioned=None,
                 tags=None, **kwargs):
        self.parent = parent
        self.manager = manager
        self.mount_name = mount_name
        self.mount_config = mount_config or {}
        self.expand_paths = expand_paths
        self.versioned = versioned
        self.tags = tags

    # ---- plumbing

    def _node(self, *args, version_id=None):
        path = '/'.join([a for a in args if a not in (None, '')])
        return self.manager.node(self.mount_name, path, version=version_id)

    @property
    def protocol(self):
        return self.mount_config.get('protocol') or 'local'

    @property
    def is_local(self):
        return self.protocol == 'local'

    @property
    def base_path(self):
        return (self.mount_config.get('base_path')
                or self.mount_config.get('path') or '')

    def expandpath(self, path):
        return expandpath(path) if self.expand_paths else path

    @property
    def location_identifier(self):
        """Local mounts share 'localfs' with the legacy local services, so a copy
        between the two worlds stays a filesystem copy. Remote mounts get an
        identifier of their own: a copy towards any other service then goes
        through content, which is always correct."""
        if self.is_local:
            return 'localfs'
        return 'genro-storage:%s/%s/%s' % (self.protocol,
                                           self.mount_config.get('bucket') or '',
                                           self.base_path.strip('/'))

    @property
    def is_versioned(self):
        if self.versioned is False:
            return False
        return self._node().capabilities.versioning

    def internal_path(self, *args, **kwargs):
        node = self._node(*args)
        resolved = node.resolved_path
        if resolved is not None:
            return resolved
        prefix = self.base_path.strip('/')
        if not prefix:
            return node.path
        return ('%s/%s' % (prefix, node.path)).rstrip('/')

    # ---- reads

    def exists(self, *args):
        return self._node(*args).exists()

    def isfile(self, *args):
        return self._node(*args).is_file()

    def isdir(self, *args):
        return self._node(*args).is_dir()

    def mtime(self, *args):
        try:
            return self._node(*args).mtime()
        except (FileNotFoundError, StorageError, ValueError):
            return None

    def size(self, *args):
        """None on a directory or a missing path: genro-storage raises on both,
        while the legacy aws_s3 service already answers None."""
        try:
            return self._node(*args).size()
        except (FileNotFoundError, StorageError, ValueError):
            return None

    def ext_attributes(self, *args):
        return self._node(*args).ext_attributes

    def md5hash(self, *args):
        try:
            return self._node(*args).md5hash()
        except (FileNotFoundError, StorageError, ValueError):
            return None

    def open(self, *args, **kwargs):
        mode = kwargs.pop('mode', 'rb')
        version_id = kwargs.pop('version_id', None)
        if version_id == '_latest_':
            version_id = None
        return self._node(*args, version_id=version_id).open(mode=mode)

    def local_path(self, *args, **kwargs):
        mode = kwargs.get('mode') or 'r'
        keep = kwargs.get('keep') or False
        if self.is_local:
            return LocalPath(fullpath=self.internal_path(*args))
        if keep:
            raise NotImplementedError(
                'local_path(keep=True) is not available on the genro-storage '
                'mount %r: the temporary file is removed when the context exits'
                % self.mount_name)
        return self._node(*args).local_path(mode='rw' if 'w' in mode else 'r')

    def children(self, *args, **kwargs):
        """Sorted by basename, as the legacy local service is: the order shows
        up in every tree built on top of this."""
        node = self._node(*args)
        if not node.exists():
            return []
        out = []
        for child in sorted(node.children(), key=lambda child: child.basename):
            if child.basename == GNRDIR_SENTINEL:
                continue
            out.append(StorageNode(parent=self.parent, path=child.path, service=self))
        return out

    def versions(self, *args):
        """Reported with the boto3 key names the legacy aws_s3 service returns,
        so the consumers of versions() need no branch on the backend."""
        if not self.is_versioned:
            return []
        out = []
        for version in self._node(*args).versions:
            etag = version.get('etag')
            out.append({
                'VersionId': version.get('version_id'),
                'IsLatest': version.get('is_latest'),
                'LastModified': version.get('last_modified'),
                'Size': version.get('size'),
                'ETag': '"%s"' % etag if etag else None,
            })
        return out

    def get_metadata(self, *args):
        return self._node(*args).get_metadata()

    def set_metadata(self, *args):
        *path, metadata = args
        return self._node(*path).set_metadata(metadata)

    # ---- writes

    def makedirs(self, *args, **kwargs):
        if not self.is_local:
            return
        self._node(*args).mkdir(parents=True, exist_ok=True)

    def mkdir(self, *args, **kwargs):
        if self.exists(*args):
            return
        if self.is_local:
            return self._node(*args).mkdir(parents=True, exist_ok=True)
        with self.open(*args + (GNRDIR_SENTINEL,), mode='w') as dotfile:
            dotfile.write('.gnrdircontent')

    def delete_file(self, *args):
        self._node(*args).delete()

    def delete_dir(self, *args):
        node = self._node(*args)
        for child in node.children():
            child_args = args + (child.basename,)
            if child.is_dir():
                self.delete_dir(*child_args)
            else:
                self._node(*child_args).delete()
        node.delete()

    def duplicateNode(self, sourceNode=None, destNode=None):
        if isinstance(destNode.service, Service):
            return self._node(sourceNode.path).copy_to(
                destNode.service._node(destNode.path))
        destNode.service.autocreate(destNode.path, autocreate=-1)
        shutil.copy2(sourceNode.internal_path, destNode.internal_path)

    def renameNode(self, sourceNode=None, destNode=None):
        if isinstance(destNode.service, Service):
            self._node(sourceNode.path).move_to(
                destNode.service._node(destNode.path))
            return destNode
        destNode.service.autocreate(destNode.path, autocreate=-1)
        shutil.move(sourceNode.internal_path, destNode.internal_path)
        return destNode

    # ---- urls and serving

    def url(self, *args, **kwargs):
        if self.is_local:
            return self.internal_url(*args, **kwargs)
        expiration = kwargs.pop('expiration', None) or 3600
        return self._node(*args).url(expires_in=expiration)

    def internal_url(self, *args, **kwargs):
        if not self.is_local:
            # The legacy aws_s3 service serves its internal urls as downloads.
            kwargs['_download'] = True
        return super().internal_url(*args, **kwargs)

    def public_url(self, *args, **kwargs):
        """A plain, non-expiring url: the object must be publicly readable, this
        only builds the address."""
        if self.is_local:
            return self.internal_url(*args, **kwargs)
        endpoint = (self.mount_config.get('endpoint_url') or '').rstrip('/')
        bucket = self.mount_config.get('bucket')
        if not (endpoint and bucket):
            return self.url(*args, **kwargs)
        return '%s/%s/%s' % (endpoint, bucket, self.internal_path(*args))

    def serve(self, path, environ, start_response, download=False, download_name=None, **kwargs):
        if not self.is_local:
            content_disposition = "inline"
            if download or download_name:
                content_disposition = "attachment; filename=%s" % (
                    download_name or self.basename(path))
            url = self.url(path, _content_disposition=content_disposition)
            if url:
                return self.parent.redirect(environ, start_response, location=url, temporary=True)
            return self.parent.not_found_exception(environ, start_response)
        fullpath = self.internal_path(path)
        if not fullpath or not os.path.exists(fullpath):
            return self.parent.not_found_exception(environ, start_response)
        if_none_match = environ.get('HTTP_IF_NONE_MATCH')
        if if_none_match:
            stats = os.stat(fullpath)
            my_none_match = "%s-%s" % (str(stats.st_mtime), str(stats.st_size))
            if my_none_match == if_none_match.replace('"', ''):
                start_response('304 Not Modified', [('ETag', '"%s"' % my_none_match)])
                return [b'']
        file_args = dict()
        if download or download_name:
            file_args['content_disposition'] = "attachment; filename=%s" % (
                download_name or os.path.basename(fullpath))
        file_responder = _SimpleFileApp(fullpath, **file_args)
        if self.parent.cache_max_age:
            file_responder.cache_control(max_age=self.parent.cache_max_age)
        return file_responder(environ, start_response)
