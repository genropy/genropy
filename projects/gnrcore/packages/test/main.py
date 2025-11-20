#!/usr/bin/env python
# encoding: utf-8

from gnr.app.gnrdbo import GnrDboTable, GnrDboPackage

class Package(GnrDboPackage):
    def config_attributes(self):
        return dict(comment='test package', sqlschema='test',
                    name_short='Test', name_long='Test', name_full='Test',_syspackage=True)

    def config_db(self, pkg):
        pass

    def loginUrl(self):
        return 'test/login'

    def packageTags(self, root):
        """Define auth tags for the test package.

        :param root: AuthTagStruct branch for this package"""
        
        # Admin permissions
        admin = root.branch('admin', description='Administration')
        admin.authTag('full_access', description='Full Access', note='Complete administrative access')
        admin.authTag('system_config', description='System Configuration', note='Configure system settings')

        # Test management
        tests = root.branch('test_management', description='Test Management')
        tests.authTag('run_tests', description='Run Tests', note='Execute test suites')
        tests.authTag('view_results', description='View Results', note='View test execution results')
        tests.authTag('configure_tests', description='Configure Tests', note='Modify test configurations')

        # Development tools
        dev = root.branch('development', description='Development')
        dev.authTag('debug_mode', description='Debug Mode', note='Enable debug features', isreserved=True)
        dev.authTag('source_viewer', description='Source Viewer', note='Access source code viewer')

class Table(GnrDboTable):
    pass

class WebPage(object):
    package_py_requires = 'gnrcomponents/source_viewer/source_viewer:SourceViewer'
