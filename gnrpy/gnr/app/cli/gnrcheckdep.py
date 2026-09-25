#!/usr/bin/env python
import sys

from gnr.core.cli import GnrCliArgParse
from gnr.app.gnrapp import GnrApp

description = "verify if all the dependencies are installed"

def main():
    parser = GnrCliArgParse(description=description)
    parser.add_argument("-i", "--install",
                        dest="install",
                        action="store_true",
                        help="Try to install the missing deps")
    parser.add_argument("-f", "--fix",
                        dest="fix",
                        action="store_true",
                        help="Try to fix dependencies by upgrading packages")
    parser.add_argument("-n", "--nocache",
                        dest="nocache",
                        action="store_true",
                        help="Don't use the local package cache")
    parser.add_argument("-v", "--verbose",
                        dest="verbose",
                        action="store_true",
                        help="Be verbose")
    parser.add_argument("-s", "--strict",
                        dest="strict",
                        action="store_true",
                        help="Fail when the packages section of instanceconfig.xml does not"
                             " declare every package reached through required_packages()")
    
    parser.add_argument("instance_name")
    options = parser.parse_args()
    app = GnrApp(options.instance_name, checkdepcli=True)
    instance_deps = app.instance_packages_dependencies

    if options.verbose:
        print("Packages loaded are")
        for entry in app.package_closure().values():
            declared = "declared" if entry['declared'] else "required by " + ", ".join(sorted(entry['required_by']))
            print(f"* {entry['code']} ({declared})")
        print(" ")
    if app.undeclared_packages:
        print(app.undeclared_packages_report())
        print(" ")
        if options.strict:
            sys.exit(4)
    
    if options.verbose:
        print("Required dependencies are")
        for k,v in instance_deps.items():
            print(f"* {k} ({', '.join(v)})")
        print(" ")
        print("Checking for installed dependencies")
        
    missing, wrong = app.check_package_missing_dependencies()

    if missing:
        dep_list = " ".join(missing)
        if options.verbose:
            print(f"\nThe following dependencies are missing: {dep_list}")
        if options.install:
            print("Installing as requested...")
            app.check_package_install_missing(nocache=options.nocache,
                                              verbose=options.verbose)
        else:
            print(f"\nPlease execute\n\npip install {dep_list}") 
            sys.exit(2)
        
    if wrong:
        print("\nCheck has detected the following wrong dependencies")
        for requested, installed in wrong:
            print(f"{requested} is requested, but {installed} found")

        if options.fix:
            print("\nTrying to fix the problem by upgrading..")
            app.check_package_install_missing(nocache=options.nocache,
                                              verbose=options.verbose,
                                              upgrading=True)

            # recheck
            missing, wrong = app.check_package_missing_dependencies()
            if wrong:
                print("\nProblem not solved, please fix manually")
            else:
                print("\nAll conflicts solved!")
               
        sys.exit(3)

    if options.verbose:
        print("Building the ESM bundles")
    try:
        output_dir, results = app.build_esm_bundles()
    except Exception as e:
        print(f"\nESM bundling failed: {e}", file=sys.stderr)
        sys.exit(5)
    if options.verbose and results is not None:
        print(f"ESM bundles in {output_dir}")

    if not missing and not wrong:
        print("All good!")
if __name__ == "__main__":
    main()
