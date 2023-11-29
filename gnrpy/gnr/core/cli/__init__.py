import argparse


class GnrCliArgParse(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if " " not in self.prog:
            print("\n\033[91m *** DEPRECATION WARNING: please use 'gnr' script! *** \033[00m\n")
            
