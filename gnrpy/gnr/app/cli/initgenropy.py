import argparse
from gnr.app.gnrdeploy import initgenropy

description = "Initialize a new genropy environment"

def main():
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('gnrdaemon_password',nargs='?')
    parser.add_argument('-N', '--no_user',help="Avoid base user",action='store_true',)
    options = parser.parse_args()
    initgenropy(gnrdaemon_password=options.gnrdaemon_password,
                avoid_baseuser=options.no_user)

if __name__ == '__main__':
    main()
