import logging
import argparse
import platform
ESC = '\033['

from gnr import VERSION

class GnrCliArgParse(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_argument("--version", action="version",
                          version="%(prog)s "+VERSION)
        self.add_argument("--timeit", action="store_true",
                          dest="timeit",
                          help="Report command execution time")

        LOGGING_LEVELS = {'notset': logging.NOTSET,
                          'debug': logging.DEBUG,
                          'info': logging.INFO,
                          'warning': logging.WARNING,
                          'error': logging.ERROR,
                          'critical': logging.CRITICAL}

        self.add_argument("--loglevel", 
                          dest="loglevel",
                          metavar="LOG_LEVEL",
                          choices=list(LOGGING_LEVELS.keys()),
                          default="warning",
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
        import gnr
        gnr.GLOBAL_DEBUG = options.debug
        return options
