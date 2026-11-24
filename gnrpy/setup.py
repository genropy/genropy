#!/usr/bin/env python3
import tomllib

import setuptools

EXCLUDE = ['*.__pycache__', '*.__pycache__.*']


def discover_packages():
    """Declare every directory under the package-dir roots as a package.

    The non-Python trees mapped under the gnr namespace (gnrjs, projects,
    dojo_libs, resources, webtools) ship their files as package data, and
    setuptools only installs data of directories declared as packages.
    """
    with open('pyproject.toml', 'rb') as f:
        package_dir = tomllib.load(f)['tool']['setuptools']['package-dir']
    packages = []
    for name, path in package_dir.items():
        packages.append(name)
        packages.extend(f'{name}.{sub}' for sub in
                        setuptools.find_namespace_packages(path, exclude=EXCLUDE))
    return packages


setuptools.setup(packages=discover_packages())
