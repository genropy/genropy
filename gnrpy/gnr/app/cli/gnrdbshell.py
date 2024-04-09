#!/usr/bin/env python
import sys
from gnr.core.cli import GnrCliArgParse
from gnr.app.gnrapp import GnrApp
        


class AutoTable(object):
    def __init__(self, pkg_name, db):
        self._package_name = pkg_name
        self._db = db
    def __getattr__(self, name):
        # cached in genropy?
        if name=='__wrapped__':  # jedi fix ?
            return self.__dir__()
        return self._db.table('%s.%s' % (self._package_name, name))

    def __dir__(self):
        pkg = self._db.package(self._package_name)
        return list(pkg.tables)

    def __str__(self):
        return "<AutoTable for package '%s'>" % self._package_name
    __repr__ = __str__

description = "an interactive helper utility for handling tables"

def main():
    try:
        import jedi
        print ("\n*** Note: jedi is installed, autocompletion may not work properly ***\n")
        # pip uninstall jedi
        # %config IPCompleter.use_jedi = False
    except:
        pass

    parser = GnrCliArgParse(description=description)
    parser.add_argument("instance_name")
    options = parser.parse_args()

    gnrapp = GnrApp(options.instance_name)
    db = gnrapp.db
    packages = list(db.packages)
    for pkg_name in packages:
        locals()[pkg_name] = AutoTable(pkg_name, db)
    print ("\nPackages: %s"%' '.join(packages))
    try:
        from IPython import embed
    except:
        print("Python", sys.version)
        print("\nMissing IPython, please install it")
        print("pip install ipython")
        sys.exit(1)
        


    # start IPython
    embed(colors="neutral", display_banner=False)


if __name__ == "__main__":
    main()
