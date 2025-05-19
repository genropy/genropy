# -*- coding: utf-8 -*-
import sys
import os
import os.path
import glob

import pytest

import gnr
from gnr.core.cli import GnrCliArgParse
from gnr.app.gnrapp import GnrApp
from gnr.dev import logger

description = "Run unit tests for all packages used by an instance"

def main():
    p = GnrCliArgParse(
        description=description
    )
    p.add_argument("instance_name")
    p.add_argument("package_name", nargs="?")
    options, pytest_options = p.parse_known_args()

    # all unknown options are passed directly to pytest
    PYTEST_ARGS = [
        '--asyncio-mode=strict',
    ] + pytest_options

    try:
        app = GnrApp(options.instance_name)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
        
    os.environ['GNR_TESTING_INSTANCE_NAME'] = options.instance_name
    
    all_packages = [p for p in app.packages()]
    if options.package_name:
        if options.package_name not in all_packages:
            print(f"Packages {options.package_name} does not belong to {options.instance_name}")
            sys.exit(2)

        all_packages = [options.package_name]

    logger.info("Testing packages %s for instance %s", ",".join(all_packages), options.instance_name)

    for package in all_packages:
        logger.info("Testing package %s", package)
        package_obj = app.packages[package]
        test_folder = os.path.join(package_obj.packageFolder, "tests")
        found_tests = glob.glob(os.path.join(test_folder, "test_*py"))
        if not found_tests:
            logger.warning("No tests found for package %s", package)
            continue

        r = pytest.main(found_tests + PYTEST_ARGS)


    logger.info("Testing instance %s", options.instance_name)
    instance_test_folder = os.path.join(app.instance_name_to_path(options.instance_name), "tests")
    instance_tests = glob.glob(os.path.join(instance_test_folder, "test_*py"))
    if not instance_tests:
        logger.warning("No tests found for instance %s", options.instance_name)
    else:
        logger.debug(f"Found instance {options.instance_name}: tests: %s", instance_tests)
        r = pytest.main(instance_tests + PYTEST_ARGS)
