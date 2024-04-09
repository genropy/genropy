#!/usr/bin/env python
import sys
import os
import os.path
import subprocess
import pkg_resources
from collections import defaultdict

from gnr.core.cli import GnrCliArgParse
from gnr.app.gnrapp import GnrApp

def get_instance_deps(instance_name):
    gnrapp = GnrApp(instance_name)
    instance_deps = defaultdict(list)
    for node in gnrapp.packages.nodes:
        deps_m = getattr(node.value, "config_dependencies", None)
        if deps_m:
            for m in deps_m():
                instance_deps[m].append(node.label)
        requirements_file = os.path.join(node.value.packageFolder, "requirements.txt")
        if os.path.isfile(requirements_file):
            with open(requirements_file) as fp:
                for line in fp:
                    instance_deps[line.strip()].append(node.label)
    return instance_deps

def check_deps_installation(deps_list):
    missing = []
    wrong = []
    for name in deps_list:
        try:
            pkg_resources.get_distribution(name)
        except pkg_resources.DistributionNotFound:
            missing.append(name)
        except pkg_resources.VersionConflict as e:
            wrong.append((e.req, e.dist))
    return missing, wrong

description = "verify if all the dependencies are installed"

def main():
    parser = GnrCliArgParse(description=description)
    parser.add_argument("-i", "--install",
                        dest="install",
                        action="store_true",
                        help="Try to install the missing deps")
    parser.add_argument("-v", "--verbose",
                        dest="verbose",
                        action="store_true",
                        help="Be verbose")
    
    parser.add_argument("instance_name")
    options = parser.parse_args()
    instance_deps = get_instance_deps(options.instance_name)




    if options.verbose:
        print("Required dependencies are")
        for k in instance_deps.keys():
            print(f"* {k}")
        print(" ")
        print("Checking for installed dependencies")

    missing, wrong = check_deps_installation(instance_deps)
    
    if missing:
        dep_list = " ".join(missing)
        print(f"\nThe following dependencies are missing: {dep_list}")
        if options.install:
            print("Installing as requested...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing)
        else:
            print(f"\nPlease execute\n\npip install {dep_list}") 

    if wrong:
        print("\nCheck has detected the following wrong dependencies")
        for requested, installed in wrong:
            print(f"{requested} is requested, but {installed} found")
          
if __name__ == "__main__":
    main()
