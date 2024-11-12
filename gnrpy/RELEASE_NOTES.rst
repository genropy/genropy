Version 24.11.12
================

Enhancements
------------

* Introduce linting for F401, with a full code check and cleanup

* Tests can use a custom postgres database server using GNR_TEST_PG_*
  env variables (HOST, PORT, USER, PASSWORD)

Version 24.11.4
===============

Enhancements
------------

* **Bag Template System**: Introduced `_template_kwargs` in the `Bag`
  class to allow template expansion using environment variables, and
  updated tests for the `Bag` template system.

* **Docker Image Workflow**: Added Docker image tagging for `develop`
  and `master` branches using project versioning, modified the GitHub
  Actions workflow for Docker image builds, adding branch name
  extraction and version handling, fixed issues with tag formatting
  and added platform-specific build configurations (amd64 and arm64).

* **Python Version Compatibility**: Added support for Python 3.12 and
  3.13 in test matrices, ensuring compatibility with newer versions,
  updated package dependencies, adding `packaging` to support version
  management.

Bug Fixes
-----
* **Dependency Management**: Replaced `pkg_resources` with
  `importlib.metadata` for package version handling to resolve
  deprecation warnings on Python >= 3.12.

* **Various Typos and Formatting Issues**: Corrected numerous typos in
  code comments, log messages, and parameter documentation,
  standardized usage of raw string literals in regular expressions,
  addressed issues in the `gnrlocale.py` and `gnrlist_test.py` files
  related to locale and list handling.

* **GitHub Actions Updates**: Fixed issues in `set-output` commands to
  use the `GITHUB_ENV` for exporting environment variables, corrected
  misplaced steps and adjusted sequence in Docker and test workflows.

* **Code Documentation**: Standardized parameter formatting in
  documentation strings, ensuring compatibility with Sphinx and other
  documentation tools, improved documentation for public methods and
  their parameters.

* **General Code Cleanup**: Removed unused imports and cleaned up
  deprecated syntax, addressed escaping issues in code to enhance
  readability and avoid conflicts in syntax highlighting, adjusted the
  usage of `locale` in the `gnrlocale` module to resolve compatibility
  issues with Babel.

Testing and Validation
----------------------

* Enhanced GitHub Actions workflows to set environment variables for
  locale settings during test execution.

* Updated `pytest` configurations to include testing across modules
  `core`, `sql`, `web`, `app`, and `xtnd`.


Version 24.10.2
===============

Bug Fixes
---------

* Reverted recent warning suppression commit which introduced a regression
  in formuleColumns
  
Version 24.10.1
===============

New Features
------------

* **Service defaultPrompt and contentEditor**: Added `initialEditType`
  as a customizable parameter for `contentEditor` and `MDEditor`,
  allowing for more flexible configuration of the initial editing
  mode.
* **FrameIndex**: Introduced `fi_get_owner_name` method to allow
  dynamic retrieval of owner names in the frame index interface.
* **PickerViewSimple**: Simplified picker views, providing a basic
  picker layout without headers.
* **Multibutton Enhancements**: Improved the multibutton widget,
  adding support for customizable item widths and content overflow
  management.

Bug Fixes
---------

* **Pattern Fixes**: Corrected the masking behavior in SQL regular
  expressions to properly handle special characters such as
  parentheses, brackets, and backslashes across multiple SQL adapters
  (DB2, PostgreSQL, MSSQL).
* **Archive and Delete Fixes**: Enhanced the `archive_and_delete`
  functionality, allowing deletion of archived records and managing
  dependencies effectively.
* **Hidden Transaction Behavior**: Adjusted the `hidden_transaction`
  behavior to prevent triggering unwanted database event
  notifications, ensuring smoother background operations.
* **Smart Open Compatibility**: Resolved issues with smart file
  opening in AWS S3 services by ensuring the correct session and
  client parameters are passed.
* **Modal Panel in FrameIndex**: Added the option to open modal panels
  in the frame index, improving the flexibility of panel management
  within the UI.
* **MD Editor Fixes**: Resolved issues with the Markdown editor's
  viewer mode, toolbar item removal, and proper character counting for
  content limits.
* **Gridbox LabeledBox**: Fixed issues with `GridboxLabeledBox`
  alignment, ensuring proper layout behavior when used with flexbox
  and formlet components.

Cosmetic Improvements
---------------------

* **Gridbox**: Minor cosmetic adjustments for better handling of grid
  layouts and labeled boxes, including improved spacing and field
  background management.
* **Picker**: Enhanced the picker interface by improving conditions
  and subtable management in tree and grid-based picker views.
* **Attachment Manager**: Updated the attachment manager to support
  video previews for common formats like MP4 and AVI, providing a more
  comprehensive file handling experience.

Performance Improvements
------------------------

* **Fake Resize Handling**: Improved the window resizing mechanism to
  ensure it only triggers when a visibility change occurs, reducing
  unnecessary event dispatches and improving performance in
  resize-intensive scenarios.
* **Dependency Tree Fix**: Optimized dependency tree processing to
  handle foreign key relations more efficiently, especially when
  dealing with `setnull` on delete operations.

General Improvements
--------------------

* **Database Notifications**: Improved the database notification
  system to allow better control over event triggering during hidden
  transactions, avoiding unnecessary notifications.
* **Menu Generation**: Updated the table resource generation script
  (`gnrmkthresource`) to allow regeneration of menus even if resources
  already exist, ensuring the menu structure stays current, using the -m switch
* **Login Group Management**: Fixed an issue where users with multiple
  groups could not log in to their non-primary groups.
* **Monitoring**: Introduced support for Sentry.io monitoring
* deploybuilder will now create the 'config' subdirectory, to support
  older instances without it
  
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
  
