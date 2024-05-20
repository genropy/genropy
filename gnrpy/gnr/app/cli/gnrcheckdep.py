#!/usr/bin/env python
import sys
import os
import os.path
import subprocess

from gnr.core.cli import GnrCliArgParse
from gnr.app.gnrapp import GnrApp

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

    app = GnrApp(options.instance_name, checkdepcli=True)
    instance_deps = app.instance_packages_dependencies
    
    if options.verbose:
        print("Required dependencies are")
        for k,v in instance_deps.items():
            print(f"* {k} ({', '.join(v)})")
        print(" ")
        print("Checking for installed dependencies")
        
    missing, wrong = app.check_package_missing_dependencies()
    
    if missing:
        dep_list = " ".join(missing)
        print(f"\nThe following dependencies are missing: {dep_list}")
        if options.install:
            print("Installing as requested...")
            app.check_package_install_missing()
        else:
            print(f"\nPlease execute\n\npip install {dep_list}") 
        sys.exit(2)
        
    if wrong:
        print("\nCheck has detected the following wrong dependencies")
        for requested, installed in wrong:
            print(f"{requested} is requested, but {installed} found")
        sys.exit(3)
    if not missing and not wrong:
        print("All good!")
if __name__ == "__main__":
    main()
