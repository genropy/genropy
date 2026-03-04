#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#--------------------------------------------------------------------------
# package       : GenroPy app - see LICENSE for details
# module gnrapp : Genro application architecture.
# Copyright (c) : 2025 Softwell Srl - Milano

import sys
import os, os.path
import json
import subprocess
import shutil
from pathlib import Path

from gnr.app.gnrapp import GnrApp
from gnr.app.gnrdeploy import PathResolver
from gnr.app import logger

class GnrProjectBuilder(object):
    """
    This object provides helpers to build/install/deploy a project,
    handling its git related dependencies, installing them etc.

    It's also used to create project's docker images.
    """

    BUILD_FILE_NAME = "build.json"
    
    def __init__(self, instance_name):
        self.instance_name = instance_name
        
        self.instance_folder = PathResolver().instance_name_to_path(self.instance_name)
        self.config_file = os.path.join(self.instance_folder,
                                        "config",
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
        main_repo_url = self.git_url_from_path(self.instance_folder)
        # get the repo name, needed for gunicorn/supervisor templates
        self.main_repo_name = self.git_repo_name_from_url(main_repo_url)
        commit = self.git_commit_from_path(self.instance_folder)
        code_repo = {
            'url': main_repo_url,
            'branch_or_commit': commit,
            'description': self.instance_name,
            'subfolder': None
            }
        _repos[main_repo_url] = code_repo
        git_repositories = list(_repos.values())
        logger.debug("Found git repositories: %s", git_repositories)
        return git_repositories


    def find_git_root(self, start_path):
        """
        Walk upward from start_path until a `.git` directory is found.
        Returns the path to the git root, or None if not found.
        """
        current = os.path.abspath(start_path)

        while True:
            git_dir = os.path.join(current, '.git')
            if os.path.isdir(git_dir):
                return current

            parent = os.path.dirname(current)
            if parent == current:
                return None

            current = parent

    def _search_local_deps(self):
        """
        Search locally installed git repository that
        act as a dependency to our project
        """
        git_repositories = {}
        # search for git repos
        instance = GnrApp(self.instance_name)
        for package, obj in instance.packages.items():
            url = self.git_url_from_path(obj.packageFolder)

            # find the local path
            local_path = self.find_git_root(obj.packageFolder)
            
            if "genropy/genropy" in url:
                continue

            description = url.split('/')[-1].replace(".git","")

            git_repositories[description] = dict(
                path=local_path,
                url=url
            )
        return git_repositories
    
    def create_config(self, save_conf=True):
        """
        Create a new build file based on the current
        enviroment
        """
        local_git_repositories = self._search_local_deps()
        git_repositories = {}
        for repo_name, repo_conf in local_git_repositories.items():
            branch_or_commit = self.git_commit_from_path(repo_conf['path'])
        
            logger.debug("Package %s is using git remote %s on branch/commit %s",
                         repo_name, repo_conf['url'],
                         branch_or_commit
                         )
        
            git_repositories[repo_name] = dict(
                url=repo_conf['url'],
                branch_or_commit=branch_or_commit,
                description=repo_name,
        )
        
        config = {'dependencies': { "git_repositories": git_repositories} }
        if save_conf:
            with open(self.config_file, "w") as wfp:
                json.dump(config, wfp, indent=4, ensure_ascii=False)
        return config

    def checkout_project(self, dest_dir, create_dest_dir=False):
        """
        Checkout the whole project inside a destination folder
        """
        dest_dir = Path(dest_dir).absolute()
        if not os.path.exists(dest_dir):
            if create_dest_dir:
                Path(dest_dir).mkdir(parents=True, exist_ok=True)
            else:
                logger.error("Destination path doesn't exists")
                sys.exit(1)

        orig_cwd = os.getcwd()
        os.chdir(dest_dir)
        for repo in self.git_repositories():
            repo_name = self.git_repo_name_from_url(repo['url'])
            logger.info(f"Checking repository {repo_name} at {repo['url']}")
            result = subprocess.run(["git", "clone", repo['url'], repo_name],
                                    capture_output=True,
                                    )
            if result.returncode == 0:
                logger.debug("Git clone for %s went ok", repo['url'])
            else:
                logger.error("Error cloning %s: %s", repo['url'], result.stderr)
                        
            os.chdir(os.path.join(dest_dir, repo_name))
            result = subprocess.run(["git", "checkout", repo['branch_or_commit']],
                                    capture_output=True
                                    )
            if result.returncode == 0:
                logger.debug("Git checkout for branch %s went ok", repo['branch_or_commit'])
            else:
                logger.error("Error checking out %s: %s", repo['branch_or_commit'], result.stderr)
                        
            os.chdir(dest_dir)
            
        os.chdir(orig_cwd)
        
        logger.info("Checkout completed")

    def update_project(self):
        """
        Read, if any, the build file from the project, and update the local
        git repositories dependencies accordingly.
        """
        local_repos = self._search_local_deps()
        config = self.config.get("dependencies", {}).get("git_repositories", {})
        
        orig_cwd = os.getcwd()
        
        for repo_name, repo in config.items():
            # if not already checked out, report the error
            if repo_name not in local_repos:
                logger.error("Repo %s is missing, please checkout", repo_name)
                continue
            
            local_path = local_repos.get(repo_name, {}).get("path", None)

            os.chdir(local_path)
            result = subprocess.run(['git','pull'])
            if result.returncode == 0:
                logger.debug("Git pull for %s went ok", repo_name)
            else:
                logger.error("Unable to pull repository '%s'", repo_name)
                continue

            
            result = subprocess.run(["git", "checkout", repo['branch_or_commit']],
                                    capture_output=True
                                    )
            if result.returncode == 0:
                logger.debug("Git checkout on %s for branch %s went ok",
                             repo_name, repo['branch_or_commit'])
            else:
                logger.error("Error checking out %s refspec %s: %s",
                             repo_name,
                             repo['branch_or_commit'], result.stderr)
                        
        os.chdir(orig_cwd)
