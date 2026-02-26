# -*- coding: utf-8 -*-
# --------------------------------------------------------------------------
# package           : GenroPy web - see LICENSE for details
# module gnrwebcore : core module for genropy web framework
# Copyright (c)     : 2004 - 2007 Softwell sas - Milano
# Written by    : Giovanni Porcari, Michele Bertoldi
#                 Saverio Porcari, Francesco Porcari , Francesco Cavazzana
# --------------------------------------------------------------------------
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

# Created by Giovanni Porcari on 2007-03-24.
# Copyright (c) 2007 Softwell. All rights reserved.
"""Genro configuration utilities.

This module provides classes and functions for reading and managing
Genro configuration files (XML and Python based), environment settings,
and site discovery.

Classes:
    ConfigStruct: Base class for loading configuration from XML or Python files.
    InstanceConfigStruct: Configuration structure for instance-specific settings.
    IniConfStruct: Configuration structure with INI file export capabilities.

Functions:
    getGnrConfig: Load the main Genro configuration Bag.
    gnrConfigPath: Determine the path to the Genro configuration directory.
    getGenroRoot: Get the root path of the Genro installation.
    setEnvironment: Set environment variables from configuration.
    getEnvironmentPath: Get the path to environment.xml.
    getEnvironmentItem: Get/set an item from environment.xml.
    getRmsOptions: Get RMS (Remote Management Service) options.
    setRmsOptions: Set RMS options in environment.xml.
    getSiteHandler: Find site path and template for a given site name.
    updateGnrEnvironment: Update the environment.xml file.
"""

from __future__ import annotations

import glob
import os
import sys
from collections import defaultdict
from typing import Any

import gnr
from gnr.core.gnrbag import Bag
from gnr.core.gnrlang import gnrImport
from gnr.core.gnrstring import slugify
from gnr.core.gnrstructures import GnrStructData
from gnr.core.gnrsys import expandpath


class ConfigStruct(GnrStructData):
    """Base configuration structure that loads from XML or Python files.

    This class extends GnrStructData to provide configuration loading
    capabilities from either XML files or Python modules with a config
    function.

    Attributes:
        config_method: Name of the method to call in Python config files.
            Defaults to 'config'.
    """

    config_method: str = "config"

    def __init__(
        self,
        filepath: str | None = None,
        autoconvert: bool = False,
        config_method: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize ConfigStruct, optionally loading from a file.

        Args:
            filepath: Path to configuration file (.xml or .py). If extension
                is omitted, tries .xml first, then .py.
            autoconvert: If True and loading from XML, convert to Python format.
            config_method: Override the default config method name.
            **kwargs: Additional arguments passed to the config method.
        """
        if config_method:
            self.config_method = config_method
        super().__init__()
        self.setBackRef()
        if not filepath:
            return
        filename, ext = os.path.splitext(filepath)
        if not ext:
            if os.path.exists("%s.xml" % filepath):
                filepath = "%s.xml" % filepath
                ext = ".xml"
            elif os.path.exists("%s.py" % filepath):
                filepath = "%s.py" % filepath
                ext = ".py"
            else:
                return
        if ext == ".py":
            m = gnrImport(filepath, avoidDup=True)
            getattr(m, self.config_method)(self, **kwargs)
        elif ext == ".xml":
            self.fillFrom(filepath)
            if len(self) and autoconvert:
                self.toPython(filepath.replace(".xml", ".py"))
        else:
            raise Exception("Wrong extension for filepath")


class InstanceConfigStruct(
    ConfigStruct
):  # REVIEW:DEAD — zero callers found in codebase
    """Configuration structure for instance-specific database settings.

    This class provides a convenience method for defining database
    configuration in instance config files.

    Attributes:
        config_method: Set to 'instanceconfig' for instance configuration.
    """

    config_method: str = "instanceconfig"

    def db(
        self,
        implementation: str = "postgres",
        dbname: str | None = None,
        filename: str | None = None,
        **kwargs: Any,
    ) -> GnrStructData:
        """Add a database configuration child node.

        Args:
            implementation: Database implementation type (e.g., 'postgres', 'sqlite').
            dbname: Database name.
            filename: Database file path (for file-based databases like SQLite).
            **kwargs: Additional database configuration options.

        Returns:
            The created child node for method chaining.
        """
        return self.child(
            "db",
            implementation=implementation,
            dbname=dbname,
            filename=filename,
            **kwargs,
        )


class IniConfStruct(ConfigStruct):
    """Configuration structure with INI file export capabilities.

    This class extends ConfigStruct to support hierarchical section/parameter
    structures that can be exported to INI file format.
    """

    def section(
        self,
        section: str | None = None,
        name: str | None = None,
        label: str | None = None,
    ) -> GnrStructData:
        """Add a section to the configuration.

        Args:
            section: Section type identifier.
            name: Section name.
            label: Display label for the section.

        Returns:
            The created section node for method chaining.
        """
        return self.child(
            "section",
            name=name,
            section=section,
            childname=label or name,
            label=label,
        )

    def parameter(
        self,
        parameter: str | None = None,
        value: Any = None,
    ) -> GnrStructData:
        """Add a parameter to the current section.

        Args:
            parameter: Parameter name (dots are converted to underscores).
            value: Parameter value.

        Returns:
            The created parameter node for method chaining.
        """
        return self.child(
            "parameter",
            parameter=parameter,
            value=value,
            childname=parameter.replace(".", "_"),
        )

    def toIniConf(self, filepath: str) -> None:
        """Export configuration to INI file format.

        Args:
            filepath: Path where the INI file will be written.
        """
        with open(filepath, "w") as f:
            self._toIniConfInner(f, self)

    def _toIniConfInner(self, filehandle: Any, b: GnrStructData) -> None:
        """Recursively write configuration nodes to INI format.

        Args:
            filehandle: Open file handle for writing.
            b: Configuration bag/structure to process.
        """
        for n in b:
            kw = dict(n.attr)
            tag = kw.pop("tag", None)
            key = kw.pop(tag)
            if tag == "section":
                filehandle.write("\n")
                section_name = kw.get("name")
                filehandle.write(
                    "[%s]\n" % ("%s:%s" % (key, section_name) if section_name else key)
                )
                if n.value:
                    subsections: dict[str, list[str]] = defaultdict(list)
                    for sn in n.value.nodes:
                        section = sn.attr.get("section")
                        if section:
                            subsections[section].append(sn.attr["name"])
                    if subsections:
                        for k, v in list(subsections.items()):
                            filehandle.write("%ss=%s\n" % (k, ",".join(v)))

            elif tag == "parameter":
                parameter_value = kw.pop("value")
                parameter = kw.pop("parameter", key)  # noqa: F841
                if n.value:
                    parameter_value = list(n.value.keys())
                filehandle.write("%s=%s" % (key, parameter_value))
            if n.value:
                self._toIniConfInner(filehandle, n.value)
            filehandle.write("\n")

    def toPython(self, filepath: str | None = None) -> None:
        """Export configuration to Python file format.

        Args:
            filepath: Path where the Python file will be written.
        """
        with open(filepath, "w") as f:
            text = """# encoding: utf-8
def config(root):"""
            f.write(text)
            self._toPythonInner(f, self, "root")

    def _toPythonInner(
        self,
        filehandle: Any,
        b: GnrStructData,
        rootname: str,
    ) -> None:
        """Recursively write configuration nodes to Python format.

        Args:
            filehandle: Open file handle for writing.
            b: Configuration bag/structure to process.
            rootname: Variable name for the current root node.
        """
        filehandle.write("\n")
        for n in b:
            kw = dict(n.attr)
            tag = kw.pop("tag")
            key = kw.pop(tag)
            label = kw.get("name") or key
            attrlist = ['u"%s"' % key]
            for k, v in list(kw.items()):
                attrlist.append('%s="%s"' % (k, v))
            if n.value:
                varname = slugify(label).replace("-", "_")
                filehandle.write(
                    "    %s = %s.%s(%s)" % (varname, rootname, tag, ", ".join(attrlist))
                )
                self._toPythonInner(filehandle, n.value, varname)
            else:
                filehandle.write("    %s.%s(%s)" % (rootname, tag, ", ".join(attrlist)))
            filehandle.write("\n")


########################################


def getSiteHandler(  # REVIEW:DEAD — zero callers found in codebase
    site_name: str,
    gnr_config: Bag | None = None,
) -> dict[str, Any] | None:
    """Find site path and template for a given site name.

    Searches through configured site directories and project directories
    to locate the specified site.

    Args:
        site_name: Name of the site to find.
        gnr_config: Optional pre-loaded Genro configuration. If None,
            loads configuration using getGnrConfig().

    Returns:
        Dictionary with 'site_path', 'site_template', and 'site_script'
        keys if found, None otherwise.
    """
    gnr_config = gnr_config or getGnrConfig()
    path_list: list[tuple[str, str | None]] = []
    gnrenv = gnr_config["gnr.environment_xml"]
    sites = gnrenv["sites"]
    projects = gnrenv["projects"]
    if sites:
        sites = sites.digest("#a.path,#a.site_template")
        path_list.extend(
            [
                (expandpath(path), site_template)
                for path, site_template in sites
                if os.path.isdir(expandpath(path))
            ]
        )
    if projects:
        projects = projects.digest("#a.path,#a.site_template")
        projects = [
            (expandpath(path), template)
            for path, template in projects
            if os.path.isdir(expandpath(path))
        ]
        for project_path, site_template in projects:
            sites = glob.glob(os.path.join(project_path, "*/sites"))
            path_list.extend([(site_path, site_template) for site_path in sites])
    for path, site_template in path_list:
        site_path = os.path.join(path, site_name)
        if os.path.isdir(site_path):
            site_script = os.path.join(site_path, "root.py")
            if not os.path.isfile(site_script):
                site_script = None
            return dict(
                site_path=site_path,
                site_template=site_template,
                site_script=site_script,
            )
    return None


def setEnvironment(gnr_config: Bag) -> None:
    """Set environment variables from Genro configuration.

    Reads environment variable definitions from the configuration and
    sets them in os.environ if not already set.

    Args:
        gnr_config: Genro configuration Bag containing environment settings.
    """
    environment_xml = gnr_config["gnr.environment_xml"]
    if environment_xml:
        if not environment_xml["environment"]:
            return
        for var, value in environment_xml.digest("environment:#k,#a.value"):
            var = var.upper()
            if not os.getenv(var):
                os.environ[str(var)] = str(value)


def getGnrConfig(
    config_path: str | None = None,
    set_environment: bool = False,
) -> Bag:
    """Load the main Genro configuration as a Bag.

    Args:
        config_path: Path to configuration directory. If None, uses
            gnrConfigPath() to determine the path.
        set_environment: If True, also set environment variables from config.

    Returns:
        Bag containing the Genro configuration.

    Raises:
        Exception: If configuration directory is missing or invalid.
    """
    config_path = config_path or gnrConfigPath()
    if not config_path or not os.path.isdir(config_path):
        raise Exception("Missing genro configuration")
    gnr_config = Bag(config_path, _template_kargs=os.environ)
    if set_environment:
        setEnvironment(gnr_config)
    return gnr_config


def gnrConfigPath(
    force_return: bool = False,
    no_virtualenv: bool = False,
) -> str | None:
    """Determine the path to the Genro configuration directory.

    Searches for configuration in the following order:
    1. GENRO_GNRFOLDER environment variable
    2. Virtual environment etc/gnr directory
    3. User home directory (~/.gnr or ~\\gnr on Windows)
    4. System-wide /etc/gnr directory

    Args:
        force_return: If True, return home config path even if it doesn't exist.
        no_virtualenv: If True, skip virtual environment check.

    Returns:
        Path to the configuration directory, or None if not found.
    """
    if "GENRO_GNRFOLDER" in os.environ:
        config_path = expandpath(os.environ["GENRO_GNRFOLDER"])
        if os.path.isdir(config_path):
            return config_path
    if (
        "VIRTUAL_ENV" in os.environ or hasattr(sys, "real_prefix")
    ) and not no_virtualenv:
        prefix = os.environ.get("VIRTUAL_ENV", sys.prefix)
        config_path = expandpath(os.path.join(prefix, "etc", "gnr"))
        return config_path
    if sys.platform == "win32":
        config_path = r"~\gnr"
    else:
        config_path = "~/.gnr"
    config_path = expandpath(config_path)
    if force_return or os.path.isdir(config_path):
        return config_path
    config_path = expandpath("/etc/gnr")
    if os.path.isdir(config_path):
        return config_path
    return None


def updateGnrEnvironment(
    updater: Bag | dict[str, Any],
) -> None:  # REVIEW:DEAD — zero callers found in codebase
    """Update the environment.xml configuration file.

    Args:
        updater: Bag or dict containing values to merge into environment.xml.
    """
    config_path = gnrConfigPath()
    environment_path = os.path.join(config_path, "environment.xml")
    environment_bag = Bag(environment_path)
    environment_bag.update(updater)
    environment_bag.toXml(environment_path, pretty=True)


def getEnvironmentPath() -> str:
    """Get the path to the environment.xml configuration file.

    Returns:
        Full path to environment.xml.
    """
    return os.path.join(gnrConfigPath(), "environment.xml")


def getEnvironmentItem(
    path: str,
    default: Any = None,
    update: bool = False,
) -> Any:
    """Get or set an item from the environment.xml configuration.

    Args:
        path: Dot-separated path to the configuration item.
        default: Default value to return (and optionally save) if not found.
        update: If True and using default, save the default to environment.xml.

    Returns:
        The configuration value, or the default if not found.
    """
    environment_path = getEnvironmentPath()
    environment_bag = Bag(environment_path)
    result = environment_bag.getItem(path)
    if result is not None:
        return result
    result = default
    if update and result is not None:
        environment_bag[path] = result
    environment_bag.toXml(environment_path, pretty=True)
    return result


def getRmsOptions() -> dict[str, Any]:
    """Get RMS (Remote Management Service) options from environment.xml.

    Returns:
        Dictionary of RMS options, or empty dict if not configured.
    """
    config_path = gnrConfigPath()
    environment_path = os.path.join(config_path, "environment.xml")
    environment_bag = Bag(environment_path)
    return environment_bag.getAttr("rms") or dict()


def setRmsOptions(rebuild: bool = False, **options: Any) -> None:
    """Set RMS (Remote Management Service) options in environment.xml.

    Args:
        rebuild: If True, replace all RMS options. If False, merge with existing.
        **options: RMS option key-value pairs to set.
    """
    config_path = gnrConfigPath()
    environment_path = os.path.join(config_path, "environment.xml")
    environment_bag = Bag(environment_path)
    environment_bag.setAttr("rms", _updattr=not rebuild, **options)
    environment_bag.toXml(environment_path, pretty=True)


def getGenroRoot() -> str:
    """Get the root path of the Genro installation.

    Returns:
        Absolute path to the Genro root directory.
    """
    return os.path.abspath(os.path.join(gnr.__file__, "..", "..", ".."))
