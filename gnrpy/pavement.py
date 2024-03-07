# Transitional paver task definition, to support
# the migration to the new build and installation
# tools.

from paver.easy import *
from paver.setuputils import setup, find_packages

@task
def install():
    print("""Deprecation error: paver is no more supported!
    
Please refer to documention on https://www.genropy.org/

'paver install' command has been replaced by:

    pip install .
""")

@task
def develop(options):
        print("""Deprecation error: paver is no more supported!
    
Please refer to documention on https://www.genropy.org/

'paver develop' command has been replaced by:

    pip install --editable .
""")


