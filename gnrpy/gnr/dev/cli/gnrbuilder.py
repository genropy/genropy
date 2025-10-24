# -*- coding: utf-8 -*-
import json
import os
import sys

from gnr.core.cli import GnrCliArgParse
from gnr.app.gnrapp import GnrApp
from gnr.dev.builder import GnrProjectBuilder
from gnr.dev import logger

description = "Build and manage a project configuration"

def main():
    p = GnrCliArgParse(
        description=description
    )
    p.add_argument('instance_name',
                   help="Name of the instance")

    subparsers = p.add_subparsers(dest='command')
    subparsers.required = True

    subparsers.add_parser(
        'check',
        help="Check if the build configuration file exists"
    )
    subparsers.add_parser(
        'generate',
        help="Generate the build configuration file if missing"
    )
    subparsers.add_parser(
        'regenerate',
        help="Force regeneration of the build configuration file"
    )
    subparsers.add_parser(
        'show',
        help="Show the build configuration file contents"
    )
    subparsers.add_parser(
        'repositories',
        help="Show all git repositories used in this project"
    )
    subparsers.add_parser(
        'update',
        help="Update all repositories according to build configuration"
    )
    checkout_parser = subparsers.add_parser(
        'checkout',
        help="Show all git repositories used in this project"
    )
    checkout_parser.add_argument("path",
                                help="Path where to execute the checkout")
    
    options = p.parse_args()

    instance = GnrApp(options.instance_name)

    builder = GnrProjectBuilder(instance)

    if options.command == 'check':
        has_config = os.path.exists(builder.config_file)
        if has_config:
            logger.info("Build configuration found at %s", builder.config_file)
            exit_code = 0
        else:
            logger.warning("Build configuration missing at %s", builder.config_file)
            exit_code = 1
    elif options.command == 'generate':
        if os.path.exists(builder.config_file):
            logger.info("Build configuration already present at %s", builder.config_file)
        else:
            builder.load_config(generate=False)
            logger.info("Build configuration generated at %s", builder.config_file)
        exit_code = 0
    elif options.command == 'regenerate':
        builder.load_config(generate=True)
        logger.info("Build configuration regenerated at %s", builder.config_file)
        exit_code = 0
    elif options.command == 'show':
        config = builder.load_config(generate=False)
        print(json.dumps(config, indent=4))
        exit_code = 0
    elif options.command == 'repositories':
        config = builder.git_repositories()
        print(json.dumps(config, indent=4))
        exit_code = 0
    elif options.command == 'update':
        builder.update_project()
        exit_code = 0
    elif options.command == 'checkout':
        builder.checkout_project(options.path)
        exit_code = 0
    else:
        logger.error("Unsupported command: %s", options.command)
        exit_code = 2

    sys.exit(exit_code)
    
