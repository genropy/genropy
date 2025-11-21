#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test suite for AuthTagStruct class.

Tests the functionality of auth tag hierarchy creation, code generation,
and iteration methods.
"""

import sys
import os

# Add gnrpy to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../gnrpy'))

import unittest
from gnr.app.gnrapp import AuthTagStruct


class TestAuthTagStruct(unittest.TestCase):
    """Test cases for AuthTagStruct class"""

    def setUp(self):
        """Create a fresh AuthTagStruct instance for each test"""
        self.auth = AuthTagStruct.makeRoot()

    def test_makeRoot_creates_instance(self):
        """Test that makeRoot() creates a valid AuthTagStruct instance"""
        self.assertIsInstance(self.auth, AuthTagStruct)
        self.assertTrue(hasattr(self.auth, '_registered_tags'))
        self.assertEqual(len(self.auth._registered_tags), 0)

    def test_branch_creation(self):
        """Test creating branches in the hierarchy"""
        adm = self.auth.branch('adm', description='Administration')
        self.assertIsInstance(adm, AuthTagStruct)

        # Check structure via XML
        xml = self.auth.toXml()
        self.assertIn('label="adm"', xml)
        self.assertIn('description="Administration"', xml)
        self.assertIn('tag="branch"', xml)

    def test_nested_branch_creation(self):
        """Test creating nested branches"""
        adm = self.auth.branch('adm', description='Administration')
        users = adm.branch('users', description='User Management')

        xml = self.auth.toXml()
        self.assertIn('label="adm"', xml)
        self.assertIn('label="users"', xml)

    def test_authTag_code_generation_simple(self):
        """Test auth tag code generation for single-level tags"""
        adm = self.auth.branch('adm')
        adm.authTag('user_management', description='User Management')

        # Find the authTag in the structure
        for path, node in self.auth.getIndex():
            if node.attr.get('tag') == 'authTag':
                code = node.attr.get('code')
                self.assertEqual(code, 'adm_user_management')
                break
        else:
            self.fail("No authTag found in structure")

    def test_authTag_code_generation_nested(self):
        """Test auth tag code generation for nested hierarchies"""
        inventory = self.auth.branch('inventory')
        warehouse = inventory.branch('warehouse')
        warehouse.authTag('manage', description='Manage Warehouse')

        # Find the authTag
        for path, node in self.auth.getIndex():
            if node.attr.get('tag') == 'authTag' and node.attr.get('label') == 'manage':
                code = node.attr.get('code')
                self.assertEqual(code, 'inventory_warehouse_manage')
                break
        else:
            self.fail("No authTag 'manage' found")

    def test_authTag_code_uniqueness_different_branches(self):
        """Test that same label in different branches generates unique codes"""
        adm = self.auth.branch('adm')
        adm_users = adm.branch('users')
        adm_users.authTag('create', description='Create User')

        sales = self.auth.branch('sales')
        sales_customers = sales.branch('customers')
        sales_customers.authTag('create', description='Create Customer')

        codes = []
        for path, node in self.auth.getIndex():
            if node.attr.get('tag') == 'authTag' and node.attr.get('label') == 'create':
                codes.append(node.attr.get('code'))

        self.assertEqual(len(codes), 2)
        self.assertIn('adm_users_create', codes)
        self.assertIn('sales_customers_create', codes)
        # Ensure they are different
        self.assertNotEqual(codes[0], codes[1])

    def test_authTag_duplicate_identifier_raises_exception(self):
        """Test that duplicate identifiers raise an exception"""
        adm = self.auth.branch('adm')
        adm.authTag('test', description='Test Tag', identifier='custom_id')

        # Try to add another tag with the same identifier
        with self.assertRaises(Exception) as context:
            adm.authTag('test2', description='Test Tag 2', identifier='custom_id')

        self.assertIn('Duplicate', str(context.exception))

    def test_invalid_branch_label_raises_exception(self):
        """Test that invalid branch labels raise an exception"""
        # Test uppercase
        with self.assertRaises(Exception) as context:
            self.auth.branch('Admin', description='Admin')
        self.assertIn('Invalid label', str(context.exception))

        # Test with spaces
        with self.assertRaises(Exception) as context:
            self.auth.branch('user management', description='User Management')
        self.assertIn('Invalid label', str(context.exception))

        # Test with dots
        with self.assertRaises(Exception) as context:
            self.auth.branch('user.management', description='User Management')
        self.assertIn('Invalid label', str(context.exception))

        # Test with dashes
        with self.assertRaises(Exception) as context:
            self.auth.branch('user-management', description='User Management')
        self.assertIn('Invalid label', str(context.exception))

    def test_invalid_authTag_label_raises_exception(self):
        """Test that invalid authTag labels raise an exception"""
        adm = self.auth.branch('adm')

        # Test uppercase
        with self.assertRaises(Exception) as context:
            adm.authTag('CreateUser', description='Create User')
        self.assertIn('Invalid label', str(context.exception))

        # Test with spaces
        with self.assertRaises(Exception) as context:
            adm.authTag('create user', description='Create User')
        self.assertIn('Invalid label', str(context.exception))

    def test_valid_labels_accepted(self):
        """Test that valid labels are accepted"""
        # These should all work without exceptions
        adm = self.auth.branch('adm')
        adm.authTag('user_management')
        adm.authTag('create')
        adm.authTag('delete_all')
        adm.authTag('view123')
        adm.authTag('test_2fa')

        # Verify they were created
        tags = list(self.auth.iterFlattenedTags())
        auth_tags = [t for t in tags if t['tag_type'] == 'authTag']
        self.assertEqual(len(auth_tags), 5)

    def test_authTag_with_extra_attributes(self):
        """Test that extra attributes are preserved"""
        adm = self.auth.branch('adm')
        adm.authTag('config', description='Configuration',
                   isreserved=True, require_2fa=True,
                   linked_table='adm.config', note='Important permission')

        for path, node in self.auth.getIndex():
            if node.attr.get('tag') == 'authTag' and node.attr.get('label') == 'config':
                self.assertEqual(node.attr.get('isreserved'), True)
                self.assertEqual(node.attr.get('require_2fa'), True)
                self.assertEqual(node.attr.get('linked_table'), 'adm.config')
                self.assertEqual(node.attr.get('note'), 'Important permission')
                break
        else:
            self.fail("authTag 'config' not found")

    def test_iterFlattenedTags_returns_all_nodes(self):
        """Test that iterFlattenedTags returns both branches and authTags"""
        adm = self.auth.branch('adm')
        adm.authTag('user_mgmt', description='User Management')
        users = adm.branch('users')
        users.authTag('create', description='Create User')

        tags = list(self.auth.iterFlattenedTags())

        # Should have: adm (branch), user_mgmt (authTag), users (branch), create (authTag)
        self.assertEqual(len(tags), 4)

        # Check types
        tag_types = [t['tag_type'] for t in tags]
        self.assertEqual(tag_types.count('branch'), 2)
        self.assertEqual(tag_types.count('authTag'), 2)

    def test_iterFlattenedTags_parent_code_hierarchy(self):
        """Test that iterFlattenedTags correctly sets parent_code"""
        adm = self.auth.branch('adm')
        adm.authTag('user_mgmt', description='User Management')
        users = adm.branch('users')
        users.authTag('create', description='Create User')

        tags = list(self.auth.iterFlattenedTags())

        # Find specific tags and check their parent_code
        for tag in tags:
            if tag['code'] == 'adm':
                self.assertIsNone(tag['parent_code'])  # Root level
            elif tag['code'] == 'adm_user_mgmt':
                self.assertEqual(tag['parent_code'], 'adm')
            elif tag['code'] == 'users':
                self.assertEqual(tag['parent_code'], 'adm')
            elif tag['code'] == 'adm_users_create':
                self.assertEqual(tag['parent_code'], 'users')

    def test_iterFlattenedTags_parent_before_children(self):
        """Test that parents always appear before their children"""
        inventory = self.auth.branch('inventory')
        products = inventory.branch('products')
        products.authTag('add', description='Add Product')

        tags = list(self.auth.iterFlattenedTags())
        codes_seen = set()

        for tag in tags:
            code = tag['code']
            parent_code = tag['parent_code']

            if parent_code:
                # Parent must have been seen already
                self.assertIn(parent_code, codes_seen,
                            f"Parent '{parent_code}' of '{code}' not seen yet")

            codes_seen.add(code)

    def test_toBag_contains_authTags_only(self):
        """Test that toBag() returns only authTags, not branches"""
        adm = self.auth.branch('adm')
        adm.authTag('user_mgmt', description='User Management')
        users = adm.branch('users')
        users.authTag('create', description='Create User')

        bag = self.auth.toBag()

        # Should only have authTags
        keys = list(bag.keys())
        self.assertEqual(len(keys), 2)
        self.assertIn('adm_user_mgmt', keys)
        self.assertIn('adm_users_create', keys)

        # Branches should not be in the bag
        self.assertNotIn('adm', keys)
        self.assertNotIn('users', keys)

    def test_toBag_values_are_labels(self):
        """Test that toBag() values are the labels"""
        adm = self.auth.branch('adm')
        adm.authTag('user_mgmt', description='User Management')

        bag = self.auth.toBag()

        self.assertEqual(bag['adm_user_mgmt'], 'user_mgmt')

    def test_complex_hierarchy(self):
        """Test a complex multi-level hierarchy"""
        # Create complex structure
        adm = self.auth.branch('adm', description='Administration')
        adm.authTag('system_config', description='System Configuration')

        users = adm.branch('users', description='User Management')
        users.authTag('create', description='Create Users')
        users.authTag('delete', description='Delete Users')

        sales = self.auth.branch('sales', description='Sales')
        sales.authTag('view_reports', description='View Reports')

        customers = sales.branch('customers', description='Customers')
        customers.authTag('create', description='Create Customers')

        # Test structure
        tags = list(self.auth.iterFlattenedTags())

        # Count elements
        branches = [t for t in tags if t['tag_type'] == 'branch']
        auth_tags = [t for t in tags if t['tag_type'] == 'authTag']

        self.assertEqual(len(branches), 4)  # adm, users, sales, customers
        self.assertEqual(len(auth_tags), 5)  # system_config, create, delete, view_reports, create

        # Verify specific codes
        auth_tag_codes = [t['code'] for t in auth_tags]
        self.assertIn('adm_system_config', auth_tag_codes)
        self.assertIn('adm_users_create', auth_tag_codes)
        self.assertIn('adm_users_delete', auth_tag_codes)
        self.assertIn('sales_view_reports', auth_tag_codes)
        self.assertIn('sales_customers_create', auth_tag_codes)


if __name__ == '__main__':
    unittest.main()
