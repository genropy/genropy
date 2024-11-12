#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# general utilities for GnrApp
import os.path
from collections import defaultdict

import gnr
from gnr.core.gnrbag import Bag
from gnr.app.gnrapp import GnrApp

class GnrAppInsightDataset(object):
    """
    Base class for insight plugins. Not to be used directly.
    """
    name = "Undefined name"
    def __init__(self, app_instance):
        self.app = app_instance
        
    def retrieve(self):
        return dict()
    
class GnrAppInsightProjectComposition(GnrAppInsightDataset):
    """
    Creates a dictionary of the composition of the project
    (framework, external package, project packages etc) with
    relative percentages.
    """
    name = "Project package composition"
    RELEVANT_EXTENSIONS = ['py', 'css','xml','js']

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
        
        framework_dir = os.path.abspath(os.path.join(os.path.dirname(gnr.__file__), "..", ".."))+os.path.sep
        framework_lines = self._count_lines_in_directory(framework_dir)
        framework_name = "genropy"
        
        extra_counters = defaultdict(int)
        project_counters = defaultdict(int)
        
        for package, obj in self.app.packages.items():
            if obj.packageFolder.startswith(framework_dir):
                continue
        
            if obj.packageFolder.startswith(project_folder):
                project_counters[obj.id] = self._count_lines_in_directory(obj.packageFolder)
            else:
                extra_counters[obj.id] = self._count_lines_in_directory(obj.packageFolder)
        
        total_lines = sum(project_counters.values()) +\
            sum(extra_counters.values()) + framework_lines
        total_percentage = 100.0

        def compute_percentage(lines):
            return dict(lines=lines, percentage=(lines/total_lines)*100)
        
        extra_counters = {k: compute_percentage(v) for k, v in extra_counters.items()}
        project_counters = {k: compute_percentage(v) for k, v in project_counters.items()}
        
        global_counters = dict(framework={"genropy": dict(lines=framework_lines,
                                                          percentage=(framework_lines/total_lines)*100)},
                               extra_packages = dict(extra_counters),
                               project_packages = dict(project_counters))
        return global_counters
    
class GnrAppInsights(object):
    """
    Creates a collections of insights about a GnrApp,
    provided its instance name
    """
    insights = dict(project_composition=GnrAppInsightProjectComposition)
    
    def __init__(self, instance_name, insight_name=None):
        self.instance_name = instance_name
        self.insight_name = insight_name
        if insight_name and insight_name not in self.insights:
            raise Exception("The requested insight is not available")
        self.app = GnrApp(instance_name)
        
    def retrieve(self, as_bag=False):
        """
        Compute the requested insight (or all of them if not specified)
        returning the dictionary of data, or as a Bag if specified through "as_bag"
        """
        if self.insight_name:
            to_process = {self.insight_name: self.insights[self.insight_name]}
        else:
            to_process = self.insights

        data = {k: v(self.app).retrieve() for k, v in to_process.items()}
        
        if as_bag:
            return Bag(data)

        return data
    
        
