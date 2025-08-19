#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  gnrgit.py
#
#  Created by Francesco Porcari
#  Copyright (c) 2018 Softwell. All rights reserved.

from dulwich.client import HttpGitClient, SSHGitClient
from dulwich.repo import Repo

# WARNING
# Skipping testing and coverage since this object assume
# a local checked-out repository and access to an external one.

class GnrGit(object): # pragma: no cover
    def __init__(self,repo_path,remote_origin=None,remote_user=None,remote_password=None):
        self.repo = Repo(repo_path)
        self.config = self.repo.get_config()
        self.remote_origin = remote_origin
        self.remote_user = remote_user
        self.remote_password = remote_password
        if self.remote_origin:
            self.remote_url = self.config.get(('remote', self.remote_origin), 'url')
            self.remote_url = self.remote_url.decode("utf-8")
            if self.remote_url.startswith('http'):
                self.remote_client = HttpGitClient(self.remote_url,
                                                   username=remote_user,
                                                   password=remote_password)
            elif self.remote_url.startswith('git@'):
                # classic git+ssh url
                # ex. git@github.com:genropy/genropy.git
                user = self.remote_url.split("@")[0]
                hostname = self.remote_url.split(":")[0].split("@")[1]
                self.remote_client = SSHGitClient(host=hostname, username=user)
            else:
                raise NotImplemented("GnrGit supports only http or ssh schemas")
             
    def get_refs(self,path):
        self.remote_client.get_refs(path)
    
    
