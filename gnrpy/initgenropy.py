import os
import argparse

from gnr.app.gnrdeploy import initgenropy

def getOptions():
    usage = "\ninitgenropy"
    parser = argparse.ArgumentParser(usage)
    parser.add_argument('gnrdaemon_password',nargs='?')
    parser.add_argument('-N', '--no_user',help="Avoid base user",action='store_true',)
    arguments= parser.parse_args()
    return arguments.__dict__

if __name__ == '__main__':
    options = getOptions()
    initgenropy(gnrpy_path=os.path.dirname(os.path.realpath(__file__)),gnrdaemon_password=options.get('gnrdaemon_password'),
                    avoid_baseuser=options.get('no_user'))