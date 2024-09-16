UPCOMING RELEASE
================

* Introduced support for Sentry.io monitoring
* deploybuilder will now create the 'config' subdirectory, to support
  older instances without it
* mkthresource allow the regeneration of the menu (-m switch) even if
  the resources already exists.

Version 24.5.30.2
=================

Fixes
-----

* Fix in prometheus webtools which introduce a depending to a newer python
  version.
  
Version 24.5.30.1
=================


New Features
------------

* Focused and Blurred Window Feature: Implemented a feature to handle
  focused and blurred windows. Also, added genroLogo as a menu line
  for developers with useful commands. (Commit: 2ad349a3b)
* Webtools for Prometheus Metrics: Added new webtools to export
  Prometheus metrics of the running instance. (Commit: 1100cac6a)
* Content Form Review and Versioning Management: Enhanced the content
  form for better review and versioning management. (Commit:
  cbf5dc355)
* New deeplinking webtools to serve mandatory payload for
  deeplinking/universal links authorization.
* New 'gnr app checkdep' cli tool to verify and install packages
  python dependencies

Fixes
-----
* GnrWsgiSite Cleanup: Cleaned up GnrWsgiSite for better performance
  and maintenance. (Commit: ae152bd1f)
* Onclick URL Fetch: Fixed issues with URL fetching on click. (Commit:
  ce4a5fa0c)
* Notification and Menucode Fixes: Resolved issues with notifications
  and menu code. (Commit: 872ce9a4e)
* Genro Cordova Fixes: Fixed several issues related to Cordova,
  including handling external menu codes and general Cordova handler
  improvements. (Commits: 287e52ca2, e414f73fb, ff7f2c0ce)
* Modal Uploader Improvements: Addressed issues with the modal
  uploader, including fixing a regression and enhancing multipart
  watermark handling. (Commits: 7dceb29ad, 38603f3d8)
* Package Dependency Handling: Improved logging for package
  dependencies and fixed issues related to parsing
  requirements.txt. (Commits: 8a2e145f2, 85e52d5b0)
* Privacy Preference Fixes: Corrected issues with privacy preferences
  in the application. (Commit: 61970b472)
* Custom Workdate in Context Window: Fixed custom workdate handling in
  the context window. (Commit: 98654d793)
* Import Fixes: Resolved issues with imports, including
  GnrModuleFinder and general import placements. (Commits: 608a4dd8f,
  6b370ae18)
* Python3 Porting: Ported utility scripts to Python 3 for better
  compatibility and future-proofing. (Commit: 6098099ef)
* Code Cleanup: Removed unnecessary debug prints and cleaned up
  commented-out lines that were no longer needed. (Commits: b7af0a8ae,
  a05bd1aac)


Version 24.4.23
===============

New Features
------------

* Cordova framework detection, and payload loading into genro's js client
* New 'gnr web inspect' cli tool to inspect site registers, filterable.
* New 'gnr web serve' alias for 'gnr web wsgiserve'.
* New 'db' namespace for gnr CLI tool, to provide alias like 'gnr db setup'
  rather than 'gnr app dbsetup'.
* Added a '--version' option to all CLI command to retrive current framework
  version, useful for bug reporting
* New 'gnr db restore'
* Added iPython dependency to developer installation profile
* Workdate can be custom or current date  
* Grouped view static (for mobile use)

  
Fixes
-----

* Mobile Stylesheets fixes 
* PDFViewer opening fixes
* Fixed 'jedi import error' on all CLI commands
* Increased unit test coverage
* Code cleanup to remove deprecated references
* Possibility to print clean html if no template is required 
* Check invalid fields in dynamic form 
  
  
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
  
