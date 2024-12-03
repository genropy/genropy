#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# general utilities for GnrApp
import re
import os.path
from collections import defaultdict
import subprocess

import gnr
from gnr.core.gnrbag import Bag
from gnr.app.gnrapp import GnrApp

RED = 31
GREEN = 32
YELLOW = 33
BLUE = 34

class GnrAppInsightDataset(object):
    """
    Base class for insight plugins. Not to be used directly.
    """
    name = "Undefined name"
    def __init__(self, app_instance):
        self.app = app_instance
        
    def retrieve(self):
        return dict()

    def pprint(self):
        print(str(self.retrieve()))
        
    def get_coloured(self, text, colour):
        return f"\033[{colour}m{text}\033[0m"
        
class GnrAppInsightGitMetrics(GnrAppInsightDataset):
    """
    Return a dictionary with git metrics regarding all
    git repositories of packages composing a project
    """
    name = "Git Metrics for project"
    
    def _run_git_command(self, command, repo_path):
        result = subprocess.run(
            ['git'] + command.split() + [repo_path],
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode != 0:
            raise Exception(result.stderr.strip())
        return result.stdout.strip()
    
    def _analyze_git_repo(self, repo_path):
        contributor_output = self._run_git_command("shortlog -s -n --all", repo_path)
        contrib_commits = defaultdict(int)
        r = dict(contrib_commit=contrib_commits)
        for line in contributor_output.splitlines():
            match = re.match(r"^\s*(\d+)\s+(.+)$", line)
            if match:
                commit_count, author_name = match.groups()
                commit_count = int(commit_count)
                contrib_commits[author_name] += int(commit_count)
                
        commit_stats = self._run_git_command("log --pretty=tformat: --numstat", repo_path)
        total_additions = 0
        total_deletions = 0
        file_metrics = defaultdict(lambda: {'additions': 0, 'deletions': 0})
        
        for line in commit_stats.splitlines():
            parts = line.split()
            if len(parts) == 3:
                additions, deletions, file_name = parts
                # Handle cases where additions or deletions are "-"
                additions = int(additions) if additions != "-" else 0
                deletions = int(deletions) if deletions != "-" else 0
                total_additions += additions
                total_deletions += deletions
                file_metrics[file_name]['additions'] += additions
                file_metrics[file_name]['deletions'] += deletions
                
        stats = dict(total_additions=total_additions,
                     total_deletions=total_deletions,
                     total_files=len(file_metrics))
        
        r['stats'] = stats
        return r
    
    def retrieve(self):
        project_folder = self.app.instanceFolder.split("instances")[0]

        framework_base_dir = os.path.abspath(os.path.join(os.path.dirname(gnr.__file__), "..", ".."))+os.path.sep
        framework_name = "genropy"
        framework_data = self._analyze_git_repo(framework_base_dir)
        
        extra_packages = dict()
        project_packages = dict()
        
        for package, obj in self.app.packages.items():
            if obj.packageFolder.startswith(framework_base_dir):
                # the package is from the framework, so same repository, don't analyze
                continue

            package_project = os.path.basename(os.path.abspath(os.path.join(obj.packageFolder, "..", "..")))
            package_id = "{}.{}".format(package_project, obj.id)

            p = self._analyze_git_repo(obj.packageFolder)
            if obj.packageFolder.startswith(project_folder):
                project_packages[package_id] = p
            else:
                extra_packages[package_id] = p
            
        global_counters = dict(framework={"genropy": framework_data},
                               extra_packages = extra_packages,
                               project_packages = project_packages
                               )
        return global_counters

    def pprint(self):
        print(self.name)
        print("="*len(self.name))
        r = self.retrieve()
        for section, data in r.items():
            section_title = section.replace("_", " ").capitalize()
            print(section_title)
            print("-"*len(section_title))
            print(" ")
            for project_component, component_data in data.items():
                print(project_component)
                print("-"*len(project_component))

                print("Contributor Commits:")
                name_col_size = max([len(k) for k in component_data['contrib_commit'].keys()])
                for author, commits in component_data['contrib_commit'].items():
                    print(f"{author:<{name_col_size}}: {commits}")

                print("")
                print("General stats")
                for item, counter in component_data['stats'].items():
                    print("{}: {}".format(item.replace("_", " ").capitalize(),
                                          counter))
                print('')
            print("")

class GnrAppInsightProjectComposition(GnrAppInsightDataset):
    """
    Creates a dictionary of the composition of the project
    (framework, external package, project packages etc) with
    relative percentages.
    """
    name = "Project package composition"
    RELEVANT_EXTENSIONS = ['py', 'css','xml','js']
    FRAMEWORK_DIRS = ['gnrpy', 'gnrjs']
    
    def _count_lines_in_file(self, file_path):
        """Counts the number of lines in a single file."""
        ext = file_path.split(".")
        if len(ext) > 1:
            if ext[-1].lower() in self.RELEVANT_EXTENSIONS:
                with open(file_path, 'rb') as filefd:
                    return sum(1 for line in filefd)
        return 0

    def _count_lines_in_directory(self, directory_path):
        """Counts the total number of lines in all files within a directory."""
        total_lines = 0
        for root, dirs, files in os.walk(directory_path):
            for filename in files:
                file_path = os.path.join(root, filename)
                total_lines += self._count_lines_in_file(file_path)
        return total_lines

    def retrieve(self):
        project_folder = self.app.instanceFolder.split("instances")[0]

        framework_base_dir = os.path.abspath(os.path.join(os.path.dirname(gnr.__file__), "..", ".."))+os.path.sep
        framework_dirs = [f"{framework_base_dir}/{x}" for x in self.FRAMEWORK_DIRS]
        framework_lines = sum([self._count_lines_in_directory(d) for d in framework_dirs])
        framework_name = "genropy"
        
        extra_counters = defaultdict(int)
        project_counters = defaultdict(int)
        project_cumulative_counters = defaultdict(int)
        
        for package, obj in self.app.packages.items():
            package_project = os.path.basename(os.path.abspath(os.path.join(obj.packageFolder, "..", "..")))
            package_id = "{}.{}".format(package_project, obj.id)
                                       
            if obj.packageFolder.startswith(project_folder):
                project_inter = project_counters[package_id] = self._count_lines_in_directory(obj.packageFolder)
            else:
                project_inter = extra_counters[package_id] = self._count_lines_in_directory(obj.packageFolder)
            project_cumulative_counters[package_project] += project_inter
            
        project_cumulative_counters[framework_name] = framework_lines
        
        total_lines = sum(project_counters.values()) +\
            sum(extra_counters.values()) + framework_lines
        total_percentage = 100.0

        def compute_percentage(lines):
            return dict(lines=lines, percentage=(lines/total_lines)*100)
        
        extra_counters = {k: compute_percentage(v) for k, v in extra_counters.items()}
        project_counters = {k: compute_percentage(v) for k, v in project_counters.items()}
        project_cumulative_counters = {k: compute_percentage(v) for k, v in project_cumulative_counters.items()}
        
        global_counters = dict(framework={"genropy": dict(lines=framework_lines,
                                                          percentage=(framework_lines/total_lines)*100)},
                               extra_packages = dict(extra_counters),
                               project_packages = dict(project_counters),
                               project_cumulative = dict(project_cumulative_counters),
                               )
        return global_counters

    def pprint(self):
        print(self.name)
        print("="*len(self.name))
        data = self.retrieve()
        for project_component, component_data in data.items():
            print(project_component.replace("_", " ").capitalize())
            print("-"*len(project_component))
            ids_max_length = max([len(x) for x in component_data.keys()])
            for package in sorted(component_data.keys()):
                p = component_data[package]
                out = f"{package:<{ids_max_length}}: {p['percentage']:=6.2f}% ({p['lines']})"
                if self.app.instanceName in package:
                    out = self.get_coloured(out, 32)
                else:
                    out = self.get_coloured(out, YELLOW)
                print(out)
            print("")
        
class GnrAppInsights(object):
    """
    Creates a collections of insights about a GnrApp,
    provided its instance name
    """
    insights = dict(project_composition = GnrAppInsightProjectComposition,
                    git_metrics = GnrAppInsightGitMetrics)
    
    def __init__(self, instance_name, insight_name=None):
        self.instance_name = instance_name
        self.insight_name = insight_name
        if insight_name and insight_name not in self.insights:
            raise Exception("The requested insight is not available")
        self.app = GnrApp(instance_name)

    def _get_insight_to_process(self):
        if self.insight_name:
            to_process = {self.insight_name: self.insights[self.insight_name]}
        else:
            to_process = self.insights
        return to_process
        
    def retrieve(self, as_bag=False):
        """
        Compute the requested insight (or all of them if not specified)
        returning the dictionary of data, or as a Bag if specified through "as_bag"
        """

        data = {k: v(self.app).retrieve() for k, v in self._get_insight_to_process().items()}
        
        if as_bag:
            return Bag(data)

        return data
    
    def pprint(self):
        for v in self._get_insight_to_process().values():
            v(self.app).pprint()

