#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import stat

from gnr.web.gnrbaseclasses import BaseComponent
from gnrpkg.sys.services.ftp import SftpService

import paramiko

class _Connection(object):
    """Wraps paramiko SFTPClient to match the interface used by SftpDirectoryResolver
    and the download/upload helpers."""

    def __init__(self, sftp, ssh_client):
        self._sftp = sftp
        self._ssh = ssh_client

    def listdir(self, path='.'):
        return self._sftp.listdir(path or '.')

    def isdir(self, path):
        try:
            return stat.S_ISDIR(self._sftp.stat(path).st_mode)
        except (FileNotFoundError, IOError):
            return False

    def stat(self, path):
        return self._sftp.stat(path)

    def get(self, remotepath, localpath, callback=None, preserve_mtime=False):
        self._sftp.get(remotepath, localpath, callback=callback)
        if preserve_mtime:
            remote_stat = self._sftp.stat(remotepath)
            os.utime(localpath, (remote_stat.st_atime, remote_stat.st_mtime))

    def put(self, localpath, remotepath, callback=None, preserve_mtime=False, confirm=True):
        self._sftp.put(localpath, remotepath, callback=callback, confirm=confirm)
        if preserve_mtime:
            local_stat = os.stat(localpath)
            self._sftp.utime(remotepath, (local_stat.st_atime, local_stat.st_mtime))

    def close(self):
        self._sftp.close()
        self._ssh.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


class Service(SftpService):
    def __init__(self, parent=None, host=None, username=None, password=None,
                 private_key=None, port=None, root=None, **kwargs):
        self.parent = parent
        self.host = host
        self.username = username
        self.password = password
        self.private_key = private_key
        self.port = port
        self.root = root

    def __call__(self, host=None, username=None, password=None, private_key=None, port=None):
        host = host or self.host
        username = username or self.username
        password = password or self.password
        private_key = private_key or self.private_key
        port = int(port or self.port or 22)

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        connect_kwargs = dict(hostname=host, port=port, username=username)
        if password:
            connect_kwargs['password'] = password
        if private_key:
            connect_kwargs['key_filename'] = private_key

        ssh.connect(**connect_kwargs)
        sftp = ssh.open_sftp()

        if self.root:
            sftp.chdir(self.root)

        return _Connection(sftp, ssh)

    def downloadFilesIntoFolder(self, sourcefiles=None, destfolder=None,
                                callback=None, preserve_mtime=None,
                                thermo_wrapper=None, **kwargs):
        if isinstance(sourcefiles, str):
            sourcefiles = sourcefiles.split(',')
        if thermo_wrapper:
            sourcefiles = thermo_wrapper(thermo_wrapper)
        if callback is None:
            def callback(curr, total):
                print('dl %i/%i' % (curr, total))
        with self(**kwargs) as sftp:
            for filepath in sourcefiles:
                basename = os.path.basename(filepath)
                getkw = dict(callback=callback)
                if preserve_mtime:
                    getkw['preserve_mtime'] = preserve_mtime
                sftp.get(filepath, os.path.join(destfolder, basename), **getkw)

    def uploadFilesIntoFolder(self, sourcefiles=None, destfolder=None,
                              callback=None, preserve_mtime=None,
                              thermo_wrapper=None, confirm=None, **kwargs):
        if isinstance(sourcefiles, str):
            sourcefiles = sourcefiles.split(',')
        if thermo_wrapper:
            sourcefiles = thermo_wrapper(thermo_wrapper)
        if callback is None:
            def callback(curr, total):
                print('up %i/%i' % (curr, total))
        with self(**kwargs) as sftp:
            for filepath in sourcefiles:
                basename = os.path.basename(filepath)
                putkw = dict(callback=callback)
                if preserve_mtime:
                    putkw['preserve_mtime'] = preserve_mtime
                if confirm:
                    putkw['confirm'] = confirm
                sftp.put(filepath, os.path.join(destfolder, basename), **putkw)


class ServiceParameters(BaseComponent):

    def service_parameters(self, pane, datapath=None, **kwargs):
        fb = pane.formbuilder(datapath=datapath)
        fb.textbox(value='^.host', lbl='Host')
        fb.textbox(value='^.username', lbl='Username')
        fb.passwordTextBox(value='^.password', lbl='Password')
        fb.textbox(value='^.private_key', lbl='Private key file path')
        fb.textbox(value='^.port', lbl='Port')
        fb.textbox(value='^.root', lbl='Root')
