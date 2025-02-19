import os
import logging
import argparse
import platform
ESC = '\033['

from gnr import VERSION
from gnr.core import gnrlog

class GnrCliArgParse(argparse.ArgumentParser):
    LOGGING_LEVELS = {
        'notset': logging.NOTSET,
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'warn': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_argument("--version", action="version",
                          version="%(prog)s "+VERSION)
        self.add_argument("--timeit", action="store_true",
                          dest="timeit",
                          help="Report command execution time")


        log_level_default = "warning"
        log_level_from_env = os.environ.get("GNR_LOGLEVEL", "").lower()
        if log_level_from_env in self.LOGGING_LEVELS:
            log_level_default = log_level_from_env
        
        self.add_argument("--loglevel", 
                          dest="loglevel",
                          metavar="LOG_LEVEL",
                          choices=list(self.LOGGING_LEVELS.keys()),
                          default=log_level_default,
                          help="Startup log level")

        self.add_argument("--debug",
                          action="store_true",
                          dest="debug",
                          help="Enable DEBUG log level")
        
        if not self.prog.startswith("gnr "):
            # FIXME: this is not efficient
            # since it needs to load the whole script tree
            # to find the name. But since the old naming
            # is deprecated, it will go away soon. Also,
            # using the old name will make the script startup slower,
            # encouraging the use of the new script naming scheme
            from gnr.core.cli.gnr import cmd
            new_name = cmd.lookup_new_name(self.prog)
            deprecation_warning_mesg = f" *** DEPRECATION WARNING: please use '{new_name}' script! *** "
            if platform.system() in ['Linux', 'Darwin']:
                print(f"{ESC}91m {deprecation_warning_mesg} {ESC}00m\n")
            else:
                print(deprecation_warning_mesg)

        
    def parse_args(self, *args, **kw):
        options =  super().parse_args(*args, **kw)
        new_log_level = options.loglevel
        gnrlog.set_gnr_log_global_level(self.LOGGING_LEVELS.get(new_log_level))
        return options
