# -*- coding: utf-8 -*-
import sys
import json

from gnr.core.cli import GnrCliArgParse
from gnr.app.gnrapp import GnrApp
from gnr.app.gnrbuilder import GnrProjectBuilder
from gnr.dev import logger

description = "Build and manage a project configuration"

def main():
    p = GnrCliArgParse(
        description=description
    )
    p.add_argument('instance_name',
                   help="Name of the instance")

    options = p.parse_args()

    instance = GnrApp(options.instance_name)

    builder = GnrProjectBuilder(instance)

    
    config = builder.load_config(generate=False)

