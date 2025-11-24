# Ticket: Comprehensive Multidb Test Suite

## Summary

Create a comprehensive test suite for the multidb package and dbstores functionality to ensure reliable multi-database operations, store configuration, and tenant isolation.

## Problem Statement

Currently, multidb functionality lacks comprehensive automated testing:

**Existing test coverage:**
- Basic store switching in `test_gnrsql.py` (lines 118-131)
- Single `test_stores()` function testing auxstore addition
- No dedicated multidb package tests
- No storetable functionality tests
- No integration tests for multi-tenant scenarios
- No tests for store activation/deactivation workflow

**Gaps in testing:**
- Storetable loading from database
- Store configuration validation
- Multi-store database operations
- Store creation and alignment (sync)
- Full-sync table behavior across stores
- Error handling for misconfigured stores
- Performance with multiple active stores
- Concurrent access to different stores
- Migration scripts for XML to storetable conversion

## Goals

1. Create comprehensive unit tests for dbstores refactoring
2. Add integration tests for multidb package functionality
3. Test storetable-based configuration
4. Validate multi-tenant isolation
5. Test store lifecycle (create, activate, sync, delete)
6. Ensure backward compatibility with existing installations

## Proposed Test Structure

### Unit Tests

**gnrpy/tests/sql/test_dbstores.py** - DBStores core functionality
```python
- test_storetable_loading_from_config()
- test_connection_params_resolution()
- test_auxstore_functionality()
- test_store_fallback_parameters()
- test_dbbranch_support()
- test_missing_store_error_handling()
- test_store_context_switching()
- test_multiple_stores_management()
- test_custom_implementation_support()
```

**gnrpy/tests/sql/test_stores_handler.py** - StoresHandler class
```python
- test_add_store()
- test_add_auxstore()
- test_remove_store()
- test_get_dbdict()
- test_create_dbstore()
- test_dbstore_align()
- test_refresh_dbstores()
- test_store_validation()
```

### Integration Tests

**projects/gnrcore/packages/multidb/tests/test_storetable.py** - Storetable functionality
```python
- test_storetable_table_creation()
- test_store_record_insertion()
- test_store_activation_workflow()
- test_active_dbstore_computed_column()
- test_multidb_getForcedStore()
- test_multidb_activateDbstore()
- test_preferences_storage_per_store()
- test_store_deletion_cleanup()
```

**projects/gnrcore/packages/multidb/tests/test_multidb_package.py** - Package-level tests
```python
- test_package_initialization()
- test_checkFullSyncTables()
- test_store_discovery_from_database()
- test_multidb_one_tables()
- test_multidb_star_tables()
- test_multidb_partition_handling()
```

### Scenario Tests

**projects/gnrcore/packages/multidb/tests/test_multidb_scenarios.py** - Real-world scenarios
```python
- test_tenant_onboarding_complete_workflow()
- test_data_isolation_between_tenants()
- test_shared_data_in_main_store()
- test_tenant_specific_preferences()
- test_cross_store_queries()
- test_migration_from_xml_to_storetable()
- test_store_backup_and_restore()
```

## Test Requirements

### Prerequisites for Tests

1. **Test Database Setup**
   - Ability to create/destroy test databases
   - Multiple database support (postgres/sqlite)
   - Test data fixtures for stores and tenants
   - Isolated test environment (no side effects)

2. **Mock Infrastructure**
   - Mock application with multidb enabled
   - Mock site with domain support
   - Mock preferences system
   - Test storetable with sample stores

3. **Fixtures**
   ```python
   @pytest.fixture
   def multidb_application():
       """Application with multidb package configured"""

   @pytest.fixture
   def storetable_with_stores():
       """Storetable with 3 test stores configured"""

   @pytest.fixture
   def isolated_test_stores():
       """Three separate test databases with sample data"""
   ```

### Test Data

Sample storetable configuration for tests:
```python
storetable = Bag()
storetable.setItem('tenant1', None,
                   dbstore='tenant1',
                   dbtemplate='standard',
                   preferences=None)
storetable.setItem('tenant2', None,
                   dbstore='tenant2',
                   dbtemplate='premium',
                   preferences=None)
```

## Key Test Scenarios

### 1. Store Configuration

**Test:** Load storetable from application config
```python
def test_storetable_loading():
    # Given: Application with storetable configured
    # When: Database initializes
    # Then: Storetable is loaded and stores are available
```

**Test:** Connection parameters with fallback
```python
def test_connection_fallback():
    # Given: Store with partial configuration
    # When: Getting connection params
    # Then: Missing params fall back to main connection
```

### 2. Store Lifecycle

**Test:** Create new store
```python
def test_create_store():
    # Given: Storetable record for new tenant
    # When: Activating the store
    # Then: Database is created and schema aligned
```

**Test:** Align store schema
```python
def test_align_store():
    # Given: Store with outdated schema
    # When: Running alignment
    # Then: Schema matches current model
```

### 3. Multi-Tenant Operations

**Test:** Data isolation between tenants
```python
def test_tenant_isolation():
    # Given: Two tenants with separate stores
    # When: Inserting data in tenant1 store
    # Then: Data not visible in tenant2 store
```

**Test:** Shared master data
```python
def test_shared_master_data():
    # Given: Table marked as multidb='*'
    # When: Activating new store
    # Then: Master data copied to new store
```

### 4. Error Handling

**Test:** Missing store configuration
```python
def test_missing_store_error():
    # Given: Reference to non-existent store
    # When: Attempting to use store
    # Then: Proper exception raised
```

**Test:** Invalid storetable record
```python
def test_invalid_storetable_record():
    # Given: Storetable record with missing dbstore
    # When: Attempting activation
    # Then: Business logic exception raised
```

### 5. Performance

**Test:** Multiple store connections
```python
def test_connection_pooling():
    # Given: 10 active stores
    # When: Switching between stores rapidly
    # Then: Connections properly pooled and reused
```

### 6. Migration

**Test:** XML to storetable migration
```python
def test_xml_migration():
    # Given: Legacy XML dbstores configuration
    # When: Running migration script
    # Then: Storetable populated with equivalent config
```

## Testing Strategy

### Test Pyramid

1. **Unit Tests (60%)**
   - Fast, isolated tests
   - Mock external dependencies
   - Focus on individual functions/methods
   - Run on every commit

2. **Integration Tests (30%)**
   - Test component interactions
   - Use real database (test instance)
   - Test package-level functionality
   - Run before merge

3. **Scenario Tests (10%)**
   - End-to-end workflows
   - Realistic use cases
   - Performance testing
   - Run nightly or pre-release

### Test Execution

```bash
# Run all multidb tests
pytest gnrpy/tests/sql/test_dbstores*.py -v
pytest projects/gnrcore/packages/multidb/tests/ -v

# Run specific test categories
pytest -k "test_storetable" -v
pytest -k "test_store_lifecycle" -v

# Run with coverage
pytest --cov=gnr.sql.gnrsql --cov=multidb -v
```

## Acceptance Criteria

- [ ] All unit tests implemented and passing
- [ ] Integration tests cover main workflows
- [ ] Scenario tests validate real-world use cases
- [ ] Test coverage > 80% for modified code
- [ ] Tests run successfully in CI/CD
- [ ] Tests document expected behavior
- [ ] Performance tests show no regression
- [ ] Migration tests validate backward compatibility

## Dependencies

**Required for testing:**
- pytest framework
- pytest-fixtures for test data
- Database test utilities (create/drop test databases)
- Mock framework for application/site objects

**Code dependencies:**
- DBStores storetable refactoring (feature/refactor-dbstores-storetable)
- Multidb package

## Timeline

**Phase 1: Unit Tests (1 week)**
- Basic dbstores tests
- Connection parameter tests
- Store handler tests

**Phase 2: Integration Tests (1 week)**
- Storetable functionality
- Package-level tests
- Store lifecycle tests

**Phase 3: Scenario Tests (1 week)**
- Multi-tenant scenarios
- Migration tests
- Performance tests

**Phase 4: Documentation & CI (2 days)**
- Test documentation
- CI/CD integration
- Coverage reporting

## Current Test Coverage Analysis

**Existing coverage:**
```
gnrpy/tests/sql/test_gnrsql.py:
- test_stores() - Basic auxstore addition (lines 118-131)
- MockApplication with dbstores=None (line 14)

Gaps:
- No storetable-specific tests
- No store activation tests
- No multidb package tests
- No tenant isolation tests
- No migration tests
```

## Test Documentation

Each test should include:
- Clear docstring explaining purpose
- Given/When/Then structure
- Expected behavior documented
- Edge cases noted
- Performance expectations (if relevant)

Example:
```python
def test_store_activation_with_master_data():
    """
    Test that activating a new store copies master data.

    Given:
        - Storetable record for new tenant
        - Tables marked with multidb='*' containing master data

    When:
        - Calling multidb_activateDbstore()

    Then:
        - New database is created
        - Schema is aligned with model
        - Master data is copied from main store
        - Store is marked as active

    Edge cases:
        - Empty master tables (should not fail)
        - Large master datasets (should be performant)
        - Failed activation (should rollback)
    """
```

## Risk Mitigation

**Risk:** Tests interfere with production data
**Mitigation:**
- Use separate test databases
- Unique naming convention (test_*)
- Automatic cleanup after tests
- Never run tests on production

**Risk:** Slow test execution
**Mitigation:**
- Parallel test execution where possible
- Use in-memory SQLite for unit tests
- Mock expensive operations
- Separate fast/slow test suites

**Risk:** Flaky tests
**Mitigation:**
- Proper test isolation
- Clear test database state
- Deterministic test data
- Retry strategy for transient failures

## Success Metrics

- Test suite runs in < 5 minutes (unit + integration)
- 0 flaky tests
- Coverage > 80% for multidb code
- All edge cases documented and tested
- CI/CD integration successful
- Tests catch real bugs before production

## Related Work

- Feature branch: `feature/refactor-dbstores-storetable`
- Existing tests: `gnrpy/tests/sql/test_gnrsql.py`
- Package: `projects/gnrcore/packages/multidb/`

## Notes

- Tests should be written in parallel with features, not after
- Consider property-based testing for configuration validation
- Performance benchmarks should be automated
- Tests serve as documentation for expected behavior
- Consider adding stress tests for many tenants (100+)

## Open Questions

- [ ] What database engines should be tested? (Postgres, SQLite, MySQL?)
- [ ] Should we test cross-database store operations?
- [ ] How to handle long-running migration tests?
- [ ] Should we mock multidb package or use real instance?
- [ ] What level of performance is acceptable for store activation?
