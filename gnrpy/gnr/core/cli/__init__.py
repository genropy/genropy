import argparse
import platform
ESC = '\033['
from gnr import VERSION

class GnrCliArgParse(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_argument("--version", action="version",
                          version="%(prog)s "+VERSION)
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

        
