Upcoming release
================

Enhancements
------------

* Added support for camera selection on image acquisition on mobile
  devices (#301)
* Introduing AuthTagStruct, a new declarative system for defining
  hierarchical permission structures in applications. It's fully
  retro-compatible.
* Added a new 'variantColumn_masked' method to sqlTable for securely
  displaying sensitive data by masking portions of it, like credit
  cards numbers, email addresses etc
* Docker images and Kubernetes deployer now support labels allowing
  multi-FQDNs deployments
* Retetion policies have been upgraded to allow tables to provide more
  complex cutoff queries.
* MDEditor improvements: Drag & Drop support, custom toolbar buttons,
  color syntax plugin, hidden preview mode, and bag mode support to
  store mardown text into nested Bag structures.
* TinyMCE is now the default editor (#219)
* Postgres database dump is now correctly monitored for runtime
  errors, like server version mismatches
* Storage handling logic has been refactored and moved out of
  GnrWsgiSite, to be handled by a dedicated storage handler proxy
  module.
  
Deprecations
------------

* the 'gnr app update' cli command has been marked as deprecated
* The "site in maintenance" feature has been deprecated and removed.
* getVolumeService() and legacy volumes configuration have been
  deprecated in favor of section 'services'
* the subdomain concept from wsgisite and gnrwebpage has been dropped (#334)

Fixes
-----

* Fixed issue with multiButtonForm, now we force norecord in order to
  hide former selected record values after record is changed
* Improved checks on genropy's packages relations and dependencies (#178, #279)
* remoteRowController handling for new rows fixes
* Mobile deployment checks retrieve the correct URL from configuration
* GLBL data is loaded automatically via upgrade script
* Directory creation for existing directory now fails silently to have tidy logs
* Improvements in app template loader
* Fixed regression on docker images labels where the main application
  repository went missing
* The python dependency loader now get the list of packages from the
  loaded app, rather than parsing the instanceconfig, since more
  package can be applied from other sources (like
  instanceconfig/default.xml), so no dependency is going missing.
* The fullcalendar widget now resizes correctly upon viewport adjustments
* DB Migrate handles correctly varchar fields with min/max sizes used
  in validation, but not supported by RDBMS.
  
Release 25.10.27
================

Overview
--------

This release includes the introduction of several deployment utilities, and several
enhancement and fixes throughout the whole framework.

PLEASE NOTE: We've started dropping support for Python version prior
to 3.10, this release introduces a preliminary warning. So you're
being warned.

Enhancements
------------

* Support for 'security.txt' and 'robots.txt' WKUs through instanceconfig
* Introduced 'deferAfterCommit' method in GnrSqlDb to executed
  callables *after* a commit
* Introduced new 'gnr web serveprod' cli command, which start a
  production grade application server. Currently based on gunicorn.
* New FAQ models and backoffice tool from docu package
* A new data retention framework has been introduced, allowing tables
  to specify a retention period, which can be overriden in specific
  deployments, and provided schedulable tasks and CLI command to
  execute the retention cutoff. Introduced an initial retention policy
  in sys.error and sys.task_execution tables. Please note that the
  policy is not effecting if a task or a cron job for the cli command
  is created, it doesn't work out-of-the-box.
* Introduced support for database adapters subclassing, to extend the
  current framework adapters with custom ones.
* Introduced 'dbbranch' db connection attributes, for database
  backends that supports branching.
* boto3 client parameters now supports regions, retro-compatible.
* Added support for multiple sub-table in the ORM.
* Removed dependency from backports.zoneinfo, which is handled directly by
  stdlib's datetime.timezone
* Improvements to 2FA and validation handling at login.
* Bag can now export to JSON format.
* Formhandler support a dismissrow event publising for grid delete
  operations.
* Code cleanup for past/future references
* App stores utilities to correctly handle integrations with native
  mobile apps (Android/iOS)
  
Develop & Deployment changes
----------------------------

* Added support for debugpy, installed via 'developer' profile.
* Introduce a self-test procedure to verify if the deployment is
  finalized for mobile app usage.
* Introduced new 'sys maintanance' instance cli command to
  enable/disable maintenance mode
* Reduced Docker image footprint by disabling local cache
* Introduced switch to 'gnr app dockerize' to create images based on development version
  of the framework, and new switch to specify a different image name
* New deployment tool to Kubernetes cluster has been introduced
  (EXPERIMENTAL), allowing also splitted container deployments.
* New commodity CLI command 'gnr web stack' is provided to run the
  entire stack with a single command.
* Package dependency installer ('gnr app checkdep') has a new '-n'
  option to disable package caching.
* Package dependencies solver/installer can now automatically
  upgrade/downgrade version in order to fix the environment,
  by using 'gnr app checkdep -f <instanceName>'.
* Test suite for package has been added, automating invocation via
  'gnr dev tests' CLI command.
* A project builder framework has been introduce to manage multi-repositoy projects.
  - **New module:** ``gnr.dev.builder``
    - Manages ``build.json`` configuration.
    - Handles Git operations (clone, checkout, update) for dependencies.
    - Provides methods to rebuild or synchronize project state.
  - **New CLI:** ``gnr dev builder``
    - Commands: ``check``, ``generate``, ``regenerate``, ``show``, ``repositories``, ``update``, ``checkout``.
  - **Integration:**
    - ``gnrdockerize`` command now uses the new builder for build context creation.
    - Simplified Docker image build pipeline with automatic repository checkout.
  - Provides groundwork for future automated build and CI/CD pipelines.

Fixes & Minor Adjustments
-----------------------------

* Updated werkzeug max_form_memory_size limit to 100M, to deal with new
  hardcoded limit in recent werkzeug releases.
* Fixed several regressions in menu resolver behavior, simplified
  methods and fixes issue with single item menus.
* Improved error handling in menu source loading.
* Refined package branch expansion and flattening logic.
* Cleaned up redundant imports and improved log consistency.
* Added stricter executable dependency checks for builder and dockerization tools.
* Handling duplicaes tables views related to user object.s
* Aws translation service regressions fixes.
* Bag file system loaders avois journal/backups files when globbing.
* Picker building issues fixes, which was ignoring disable flag
* Logging cleanup

Migration Notes
-----------------------------

* Review and adjust data retention policies under ``/sys/dataretention``.
* Validate custom menu or branch logic against the simplified menu resolver.


Version 25.09.17
================

Bug fixing release, properly handle database connection close on raw
database executions.

Version 25.08.12
================

Bug fixing release, correct malformed publish action in app preferences

Version 25.04.10
================

Overview
--------

This release delivers major improvements across the database migration
tooling, PostgreSQL adapter, Docker tooling, UI components (especially
attachment and media handling), and the web server infrastructure. It
also introduces a WSGI testing framework, endpoint handling for
tables, fixes to ensure compatibility with various Python versions.

Enhancements
------------

* **General Code Improvements**:
  * Introduced SQL comment decorators for better traceability in SQL execution.
  * Standardized decorator patterns across the codebase for clarity.
  * `_documentation` storage is now used for **locally generated** documentation files, improving file management.
  * **Removed `httplib2`**, replacing it with `requests`, which is more actively maintained. 
  * **Removed `future` dependency**, since Python 3 is now the baseline. 
  * Eliminated **redundant** runtime imports to **reduce startup overhead**.
  * Removed **`simplejson`**, since `json` is part of Python’s standard library.
  - Removed **unused imports** across multiple files.
    
* **SQL Improvements**:
  * Enhanced database migration logic by improving error handling for relation-based exceptions.
  * The `GNR_GLOBAL_DEBUG` flag was removed, and `gnr db migrate` now defaults to **INFO** log level instead of DEBUG.
  * Improved `checkRelationIndex()` to log more descriptive errors when an invalid relation is encountered.
  * Improved handling of deferred relations and indexing for tenant schemas.
  * **New `#BETWEEN` syntax** added for SQL queries, supporting range
    filtering (e.g., dates, integers), which include the **upper
    bound** by default.
  * Excluded unique constraints that overlap with primary keys.
  * Added support for PostgreSQL extensions in migrations, including:
    * Commands to create extensions.
    * Integration with the migration framework.
  * Added event triggers to the migration structure.
  * **New `--inspect` flag for `gnr db migrate`**. Outputs a zip file
    with SQL schema, DB structure in JSON, ORM state, and planned SQL
    changes.
  * Added support to avoid table creation if columns are empty.
  * Centralized UNIQUE constraint generation (`addColumnUniqueConstraint()` method).
  * Improved diff and handler mechanism with default fallback for missing handlers.
  * New test cases covering unique columns and empty tables.

* **PostgreSQL Utilities**:
  * Introduced new utilities for monitoring PostgreSQL performance:
    * Queries for most-used indexes and sequential scans.
    * Autovacuum status monitoring.
    * Top and least-efficient queries statistics.

* **Database Schema**:
  * Added support for extension management in migration commands.
  * Introduced structured column grouping (`colgroup_label`, `colgroup_name_long`) for better schema organization.
  * Refactored column width estimation logic to use **a lookup table** for improved accuracy.
  * Enhanced column width calculations when handling **empty tables**. 
  * Injected column group metadata into table models to improve **attribute management**. 

* **Database adapters**:
  * Updated PostgreSQL adapter to handle `DEFERRABLE` and `INITIALLY DEFERRED` constraints.
  * Added support for capabilities declaration inside of database
    adapter, in order to conditionally execute specific tasks base on such
    specific capabilities.
  * Introduced 'postgres3' database adapter which uses the psycopg3 driver.
  * Aligned adapters inheritance method and added test coverage for it
  * Improved FK detection with ordering preserved.
  * Extended constraint introspection logic for better diff generation.
  * Multikey sort support for foreign keys.
  * Ordered foreign key extraction for better reproducibility.
  - The `gnr db migrate` command recognizes adapter-specific
    capabilities, ensuring better database compatibility.

* **Logging infrastructure**:
  * Introduced a consistent usage of python logging inside the framework.
  * All CLI commands provide a `--loglevel` options to set the logging level.
  * Logging levels can be also defined using `GNR_LOGLEVEL` env var.
  * `sys` package provide a minimale UI to control levels for each
    package of the framework.
  * Logging captures **all** exceptions for model relation validation errors.
    
* Added 'gnr dev bugreport <instance name>' to create a report of
  the current environment the instance is using, for more complete
  bug reports - please see `--help` for possible usage

* **Sphinx Export Enhancements**
  * Improved **error handling** when exporting documentation to **Sphinx**.
  * Missing images will **no longer break** the export process. 
  * Removed redundant configuration settings for **handbook preferences**. 
  * Instead of spawning an **external** Sphinx process, the framework now calls the **Sphinx build API directly**.

* **AttachManager Enhancements**:
  - Supports inline preview for images with zoom-in feature.
  - Conditional PDF viewer usage based on file extension.
  - Reworked iframe viewer logic for better handling of images/videos/docs.

* **Login Reload Fix**:
  * Removed `gnrtoken` from reload URLs to avoid state duplication.

- **PDF/Image Preview Detection Logic**:
  - Refined JS detection of when to use PDF viewer vs inline display.

- **GnrWsgiSite refactoring**:
  - Safer fallback on bad URLs or missing packages.
  - Better modularity in `UrlInfo` routing logic.
  - Handles edge cases like `..//etc/passwd` to harden path traversal.

- **Werkzeug Compatibility Patch**:
  - Fix for subcommand CLI trick used by `gnr` that breaks Python 3.8 autoreloader.

Docker Tooling
--------------

* Introducing a new docker image creation, based on the instance configuration
* Image creation and pushing towards registry
* Images are labeled with the details of all packages/repositoty involved.

Test Infrastructure
-------------------

* Added a **minimal `instanceconfig.xml`** with **framework-only packages** for unit testing.
* Expanded SQL **common tests** by adding a new `location` table definition. 
* Improved **test suite structure** to follow a **package-based layout**. 
* Enhanced unit tests for SQL migration features and removed obsolete test cases.
* Introduced `WSGITestClient` and `ExternalProcess` for end-to-end daemon testing.
* Test coverage for API key management, storage paths, routing logic, and page serving.
* Test coverage on unique constraints, foreign keys, and empty table handling.
* Test for print endpoint and variant column handler behavior.

Bug Fixes
---------

* Resolved issues with unused imports that caused linting errors.
* Fixed PostgreSQL unique constraint overlaps with primary keys.
* Eliminated runtime import artifacts and unused decorators.
* Removed deprecated mobile meta attributes.
* Corrected unique removal syntax from test fixtures.
* **MDEditor Focus Issue**
  * Fixed an issue where **MDEditor** would **lose focus**, leading to unsaved changes. 
  * Implemented an **event listener** to save changes upon focus loss.

* **SQL Query Fixes**
  * Fixed incorrect **column width calculations** in `ThResourceMaker`. :contentReference[oaicite:33]{index=33}
  * Ensured `#BETWEEN` syntax correctly handles **blank values**. :contentReference[oaicite:34]{index=34}
  * SQL **range comparisons** now consistently include the **upper bound**. :contentReference[oaicite:35]{index=35}



Removed / Deprecated / Breaking changes
---------------------------------------

- **Removed**: legacy `deepdiff` in favor of `dictdiffer`. Update your environment accordingly.
- **Removed**: obsolete Closure Compiler support.
- **Removed**: redundant iframe/viewer JS logic, refactored AttachManager handlers.

Upgrade Instructions
--------------------

* Recommended for every upgrade, to reinstall the framework using the original installation method in order to
  have dependencies working correctly.
* **Update your SQL queries** to properly utilize **`#BETWEEN`** syntax changes.
- **Review migration logs**, as error handling for relations has changed.
- **Reconfigure handbook settings**, as redundant preferences were removed.

Version 24.12.23
================

* Bugfix release, avoid deadlock on tasks 
  

Version 24.12.03
================

* introduce gnr.app.gnrutils module, for GnrApp utilities. First
  utility is GnrAppInsights, which retrieve statistical information
  about a specific GnrApp, with plugin support. Includes a new command
  line tool 'gnr app insights' to retrieve and show the statistics.

* all CLI tools have a common --timeit options that measure the
  execution time of the underlying command
  
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
---------

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
  
