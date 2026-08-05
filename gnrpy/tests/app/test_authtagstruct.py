"""
Test suite for AuthTagStruct class.

Tests the functionality of auth tag hierarchy creation, code generation,
and iteration methods.

Note: The generateAuthCode() method excludes the first level (package level)
from the generated code. This is by design - when packageTags() is called,
the package branch is created at root level, and the auth codes should not
include the package name prefix.

Example:
    root.branch('mypackage')  # Package level - excluded from codes
        .branch('admin')       # First real level
            .authTag('edit')   # Code will be 'admin_edit', not 'mypackage_admin_edit'
"""

import pytest
from common import BaseGnrAppTest
import gnr.app.gnrapp as ga


class TestAuthTagStruct(BaseGnrAppTest):
    """Test cases for AuthTagStruct class"""

    def setup_method(self, method):
        """Create a fresh AuthTagStruct instance for each test"""
        self.auth = ga.AuthTagStruct.makeRoot()

    def test_makeRoot_creates_instance(self):
        """Test that makeRoot() creates a valid AuthTagStruct instance"""
        assert isinstance(self.auth, ga.AuthTagStruct)
        assert hasattr(self.auth, '_registered_tags')
        assert len(self.auth._registered_tags) == 0

    def test_branch_creation(self):
        """Test creating branches in the hierarchy"""
        adm = self.auth.branch('adm', description='Administration')
        assert isinstance(adm, ga.AuthTagStruct)

        # Check structure via XML
        xml = self.auth.toXml()
        assert 'label="adm"' in xml
        assert 'description="Administration"' in xml
        assert 'tag="branch"' in xml

    def test_nested_branch_creation(self):
        """Test creating nested branches"""
        adm = self.auth.branch('adm', description='Administration')
        users = adm.branch('users', description='User Management')

        xml = self.auth.toXml()
        assert 'label="adm"' in xml
        assert 'label="users"' in xml

    def test_authTag_code_generation_simple(self):
        """Test auth tag code generation for single-level tags.

        Note: First level (package level) is excluded from code generation.
        So adm.authTag('user_management') generates 'user_management', not 'adm_user_management'
        """
        adm = self.auth.branch('adm')
        adm.authTag('user_management', description='User Management')

        # Find the authTag in the structure
        found = False
        for path, node in self.auth.getIndex():
            if node.attr.get('tag') == 'authTag':
                code = node.attr.get('code')
                # First level (adm) is excluded, so code is just 'user_management'
                assert code == 'user_management'
                found = True
                break
        assert found, "No authTag found in structure"

    def test_authTag_code_generation_nested(self):
        """Test auth tag code generation for nested hierarchies.

        Note: First level is excluded. So inventory.warehouse.manage generates 'warehouse_manage'
        """
        inventory = self.auth.branch('inventory')
        warehouse = inventory.branch('warehouse')
        warehouse.authTag('manage', description='Manage Warehouse')

        # Find the authTag
        found = False
        for path, node in self.auth.getIndex():
            if node.attr.get('tag') == 'authTag' and node.attr.get('label') == 'manage':
                code = node.attr.get('code')
                # First level (inventory) excluded, so code is 'warehouse_manage'
                assert code == 'warehouse_manage'
                found = True
                break
        assert found, "No authTag 'manage' found"

    def test_authTag_code_uniqueness_different_branches(self):
        """Test that same label in different branches generates unique codes.

        Note: First level is excluded from codes. So:
        - adm.users.create -> 'users_create'
        - sales.customers.create -> 'customers_create'
        """
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

        assert len(codes) == 2
        # First level excluded from codes
        assert 'users_create' in codes
        assert 'customers_create' in codes
        # Ensure they are different
        assert codes[0] != codes[1]

    def test_authTag_duplicate_identifier_raises_exception(self):
        """Test that duplicate identifiers raise an exception"""
        adm = self.auth.branch('adm')
        adm.authTag('test', description='Test Tag', identifier='custom_id')

        # Try to add another tag with the same identifier
        with pytest.raises(Exception) as excinfo:
            adm.authTag('test2', description='Test Tag 2', identifier='custom_id')

        assert 'Duplicate' in str(excinfo.value)

    def test_valid_labels_with_mixed_case_accepted(self):
        """Test that labels with mixed case are accepted.

        The framework allows any valid Python identifier (letters, numbers, underscore).
        This is intentional - the framework does not enforce snake_case as each
        application developer can choose their own naming convention.
        """
        adm = self.auth.branch('adm')
        # These should all work - valid Python identifiers
        adm.authTag('userManagement')  # camelCase
        adm.authTag('CreateUser')      # PascalCase
        adm.authTag('user_management') # snake_case
        adm.authTag('view123')
        adm.authTag('_private')

        # Verify they were created
        tags = list(self.auth.iterFlattenedTags())
        auth_tags = [t for t in tags if t['tag_type'] == 'authTag']
        assert len(auth_tags) == 5

    def test_invalid_labels_with_special_chars_rejected(self):
        """Test that labels with invalid characters are rejected"""
        adm = self.auth.branch('adm')

        # Test with spaces
        with pytest.raises(Exception) as excinfo:
            adm.authTag('create user', description='Create User')
        assert 'Invalid label' in str(excinfo.value)

        # Test with dots
        with pytest.raises(Exception) as excinfo:
            adm.authTag('user.create', description='User Create')
        assert 'Invalid label' in str(excinfo.value)

        # Test with dashes
        with pytest.raises(Exception) as excinfo:
            adm.authTag('user-create', description='User Create')
        assert 'Invalid label' in str(excinfo.value)

    def test_invalid_branch_labels_rejected(self):
        """Test that branch labels with invalid characters are rejected"""
        # Test with spaces
        with pytest.raises(Exception) as excinfo:
            self.auth.branch('user management', description='User Management')
        assert 'Invalid label' in str(excinfo.value)

        # Test with dots
        with pytest.raises(Exception) as excinfo:
            self.auth.branch('user.management', description='User Management')
        assert 'Invalid label' in str(excinfo.value)

        # Test with dashes
        with pytest.raises(Exception) as excinfo:
            self.auth.branch('user-management', description='User Management')
        assert 'Invalid label' in str(excinfo.value)

    def test_authTag_with_extra_attributes(self):
        """Test that extra attributes are preserved"""
        adm = self.auth.branch('adm')
        adm.authTag('config', description='Configuration',
                   isreserved=True, require_2fa=True,
                   linked_table='adm.config', note='Important permission')

        found = False
        for path, node in self.auth.getIndex():
            if node.attr.get('tag') == 'authTag' and node.attr.get('label') == 'config':
                assert node.attr.get('isreserved') == True
                assert node.attr.get('require_2fa') == True
                assert node.attr.get('linked_table') == 'adm.config'
                assert node.attr.get('note') == 'Important permission'
                found = True
                break
        assert found, "authTag 'config' not found"

    def test_iterFlattenedTags_returns_all_nodes(self):
        """Test that iterFlattenedTags returns both branches and authTags"""
        adm = self.auth.branch('adm')
        adm.authTag('user_mgmt', description='User Management')
        users = adm.branch('users')
        users.authTag('create', description='Create User')

        tags = list(self.auth.iterFlattenedTags())

        # Should have: adm (branch), user_mgmt (authTag), users (branch), create (authTag)
        assert len(tags) == 4

        # Check types
        tag_types = [t['tag_type'] for t in tags]
        assert tag_types.count('branch') == 2
        assert tag_types.count('authTag') == 2

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
                assert tag['parent_code'] is None  # Root level
            elif tag['code'] == 'user_mgmt':  # First level excluded from code
                assert tag['parent_code'] == 'adm'
            elif tag['code'] == 'users':
                assert tag['parent_code'] == 'adm'
            elif tag['code'] == 'users_create':  # First level excluded
                assert tag['parent_code'] == 'users'

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
                assert parent_code in codes_seen, \
                    f"Parent '{parent_code}' of '{code}' not seen yet"

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
        assert len(keys) == 2
        # First level (adm) excluded from codes
        assert 'user_mgmt' in keys
        assert 'users_create' in keys

        # Branches should not be in the bag
        assert 'adm' not in keys
        assert 'users' not in keys

    def test_toBag_values_are_labels(self):
        """Test that toBag() values are the labels"""
        adm = self.auth.branch('adm')
        adm.authTag('user_mgmt', description='User Management')

        bag = self.auth.toBag()

        # First level excluded from code
        assert bag['user_mgmt'] == 'user_mgmt'

    def test_complex_hierarchy(self):
        """Test a complex multi-level hierarchy.

        Note: First level (package level) is excluded from generated codes.
        """
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

        assert len(branches) == 4  # adm, users, sales, customers
        assert len(auth_tags) == 5  # system_config, create, delete, view_reports, create

        # Verify specific codes - first level (adm, sales) excluded
        auth_tag_codes = [t['code'] for t in auth_tags]
        assert 'system_config' in auth_tag_codes
        assert 'users_create' in auth_tag_codes
        assert 'users_delete' in auth_tag_codes
        assert 'view_reports' in auth_tag_codes
        assert 'customers_create' in auth_tag_codes

    def test_custom_identifier_overrides_auto_generation(self):
        """Test that custom identifier parameter overrides auto-generated code"""
        adm = self.auth.branch('adm')
        adm.authTag('config', description='Configuration', identifier='my_custom_code')

        found = False
        for path, node in self.auth.getIndex():
            if node.attr.get('tag') == 'authTag' and node.attr.get('label') == 'config':
                code = node.attr.get('code')
                assert code == 'my_custom_code'
                found = True
                break
        assert found, "authTag 'config' not found"

    def test_deeply_nested_hierarchy(self):
        """Test that deeply nested hierarchies generate correct codes.

        Given: pkg.level1.level2.level3.tag
        Expected code: level1_level2_level3_tag (pkg excluded)
        """
        pkg = self.auth.branch('pkg')
        level1 = pkg.branch('level1')
        level2 = level1.branch('level2')
        level3 = level2.branch('level3')
        level3.authTag('mytag', description='My Tag')

        found = False
        for path, node in self.auth.getIndex():
            if node.attr.get('tag') == 'authTag' and node.attr.get('label') == 'mytag':
                code = node.attr.get('code')
                # First level (pkg) excluded
                assert code == 'level1_level2_level3_mytag'
                found = True
                break
        assert found, "authTag 'mytag' not found"
