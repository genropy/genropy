import argparse


class GnrCliArgParse(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.prog.startswith("gnr "):
            # FIXME: this is not efficient
            # since it needs to load the whole script tree
            # to find the name. But since the old naming
            # is deprecated, it will go away soon. Also,
            # using the old name will make the script startup slower,
            # encouraging the use of the new script naming scheme
            from gnr.core.cli.gnr import cmd
            new_name = cmd.lookup_new_name(self.prog)
            print(f"\n\033[91m *** DEPRECATION WARNING: please use '{new_name}' script! *** \033[00m\n")
            
