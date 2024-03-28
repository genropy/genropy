UPCOMING RELEASE
================

* Availabily for signed URLs, including timestamped ones.
* New 'gnr web inspect' cli tool to inspect site registers, filterable.
* New 'gnr web serve' alias for 'gnr web wsgiserve'.
* New 'db' namespace for gnr CLI tool, to provide alias like 'gnr db setup'
  rather than 'gnr app dbsetup'.


Version 24.3.8
==============

* Minimum Python version required: 3.8
* Support up to Python 3.12
* Removed usage of Paver for building and installation
* Building and installation now relies on pip/pyproject/setuptools
* Introduced profile installation
* Improved test coverage
* Introduced the generic 'gnr' command line tool to access all CLI
  functions. Old scripts are maintained for retrocompatibility.
  
