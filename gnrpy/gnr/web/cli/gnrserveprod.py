#!/usr/bin/env python
# encoding: utf-8

import os
    
from gunicorn.app.base import BaseApplication
from gunicorn.config import Config as GunicornConfig

from gnr.web.gnrwsgisite import GnrWsgiSite

description = """Start production server for site"""

def load_env_config(prefix="GNR_GUNICORN_"):
    """
    Extract gunicorn options from environment variables,
    to control che daemon behaviour/configuration from enviroment
    """
    config = {}
    for key, val in os.environ.items():
        if key.startswith(prefix):
            gunicorn_key = key[len(prefix):].lower().replace("_", "-")
            config[gunicorn_key] = val
    return config

def load_config_file(path):
    """
    Load gunicorn configuration file - when extending
    from BaseApplication, it's our duty to handle this
    option
    """
    config = {}
    with open(path) as f:
        code = compile(f.read(), path, 'exec')
        exec(code, config)
    return {
        k: v for k, v in config.items()
        if not k.startswith("__")
    }

def parse_cli_args():
    """
    extend the gunicorn argparse.Parser with our settings
    """
    c = GunicornConfig()
    cli_parser = c.parser()
    cli_parser.add_argument('instance_name')
    return {k: v for k, v in vars(cli_parser.parse_args()).items() if v is not None}

def get_gnr_wsgi_application(instance_name):
    """
    Create wsgi application instance
    """
    site = GnrWsgiSite(instance_name)
    
    def application(environ,start_response):
        return site(environ,start_response)
    
    return application

class GnrProductionServer(BaseApplication):
    """
    Http server for our application, wrapping
    a wsgi server of choice (currently gunicorn)
    """
    def __init__(self, app, options):
        self.application = app
        self.options = options
        super().__init__()

    def load_config(self):
        for key, value in self.options.items():
            if key in self.cfg.settings:
                self.cfg.set(key, value)

        # override logging settings to use
        # framework's one, to have a consistent
        # output and behaviour
        logconfig_dict = {
            "version": 1,
            "disable_existing_loggers": False,
            "handlers": {
                "console": {
                    "class": 'gnr.core.loghandlers.gnrcolour.GnrInstanceColourStreamHandler',
                    "stream": "ext://sys.stdout",
                    "instance_name": self.options.get("instance_name", "UNKNOWN")
                }
                    },
            "loggers": {
                "gunicorn.error": {"handlers": ["console"]},
                "gunicorn.access": {"handlers": ["console"]},
            }
        }
        self.cfg.set("logconfig_dict", logconfig_dict)
        
    def load(self):
        return self.application

def main():
    
    env_config = load_env_config()
    cli_config = parse_cli_args()
    app = get_gnr_wsgi_application(cli_config.get("instance_name"))

    file_config = {}
    if "config" in cli_config:
        file_config = load_config_file(cli_config["config"])

    # precedence order: command line options, environment, configuration file
    combined_config = {**file_config, **env_config, **cli_config}        
    GnrProductionServer(app, combined_config).run()

if __name__ == "__main__":
    main()
