#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#--------------------------------------------------------------------------
# package       : GenroPy app - see LICENSE for details
# module gnrapp : Genro application architecture.
# Copyright (c) : 2025 Softwell Srl - Milano

import sys
import os.path
import json
import subprocess
import shutil

from gnr.app import logger

class GnrProjectBuilder(object):
    """
    This object provides helpers to build/install/deploy a project,
    handling its git related dependencies, installing them etc.

    It's also used to create project's docker images.
    """

    BUILD_FILE_NAME = "build.json"
    
    def __init__(self, instance):
        self.instance = instance
        self.config_file = os.path.join(self.instance.instanceFolder,
                                        self.BUILD_FILE_NAME)
        require_executables = ['git']
        for executable in require_executables:
            if shutil.which(executable) is None:
                logger.error("Missing executable %s - please install", executable)
                sys.exit(1)
                
        logger.debug("Build configuration file: %s", self.config_file)
        
    def load_config(self, generate=False):
        """
        Load the configuration file
        """
        if not os.path.exists(self.config_file):
            # generate a build configuration analyzing the instance
            logger.warning(f"Build file configuration not found, creating one from current status")
            config = self.create_config()
        elif generate:
            logger.warning(f"Build file configuration found, but forcing autogeneration")
            config = self.create_config()
        else:
            logger.info("Found build configuration in instance folder")
            config = json.load(open(self.config_file))

        return config

    @property
    def config(self):
        return self.load_config()
    
    def git_url_from_path(self, path):
        """
        Retrieve the repository URL for a given local path
        """
        url = subprocess.check_output(
            ["git", "remote", "get-url", "origin"],
            cwd=path).decode().strip()
        
        logger.debug("For path %s found git url: %s", path, url)
        return url

    def git_commit_from_path(self, path):
        """
        Get the current git commit for a given local path
        """
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=path).decode().strip()

    def git_branch_from_path(self, path):
        """
        Get the current branch for a given local path
        """
        return subprocess.check_output(
            ["git", "branch", "--show-current"],
            cwd=path).decode().strip()
    
    def git_repo_name_from_url(self, url):
        """
        Extract the repository name from its url
        """
        return url.split("/")[-1].replace(".git", "")

    def git_repositories(self):
        """Get a list of all Git repositories for this project."""
        _repos = {}
        git_config = self.config.get("dependencies", {}).get("git_repositories", {})
        for k, repo_conf in git_config.items():
            repo = {
                'url': repo_conf.get('url'),
                'branch_or_commit': repo_conf.get('branch_or_commit', 'master'),
                'subfolder': repo_conf.get("subfolder", None),
                'description': repo_conf.get("description", "No description")
            }
            _repos[repo_conf.get('url')] = repo

        # Include the instance repository too
        os.chdir(self.instance.instanceFolder)
        main_repo_url = self.git_url_from_path(self.instance.instanceFolder)
        # get the repo name, needed for gunicorn/supervisor templates
        self.main_repo_name = self.git_repo_name_from_url(main_repo_url)
        commit = self.git_commit_from_path(self.instance.instanceFolder)
        code_repo = {
            'url': main_repo_url,
            'branch_or_commit': commit,
            'description': self.instance.instanceName,
            'subfolder': None
            }
        _repos[main_repo_url] = code_repo
        git_repositories = list(_repos.values())
        logger.debug("Found git repositories: %s", git_repositories)
        return git_repositories
    
    def create_config(self, save_conf=True):
        """
        Create a new build file based on the current
        enviroment
        """
        git_repositories = {}
        # search for git repos
        for package, obj in self.instance.packages.items():
            url = self.git_url_from_path(obj.packageFolder)

            if "genropy/genropy" in url:
                continue
            
            branch_or_commit = self.git_commit_from_path(obj.packageFolder)
            description = url.split('/')[-1].replace(".git","")
            logger.debug("Package %s is using git remote %s on branch/commit %s",
                         obj.packageFolder, url,
                         branch_or_commit
                         )

            git_repositories[description] = dict(
                url=url,
                branch_or_commit=branch_or_commit,
                description=description
            )
            
        config = {'dependencies': { "git_repositories": git_repositories} }
        if save_conf:
            with open(self.config_file, "w") as wfp:
                json.dump(config, wfp, indent=4, ensure_ascii=False)

        return config
