# Ticket: DBStores Storetable Refactoring

## Summary

Modernize database store configuration management by moving from XML files to database-stored configuration (storetable), enabling dynamic configuration and better deployment practices.

## Description

Currently, multi-database (multidb) configurations are managed through XML files that require file system access and often need server restarts for changes. This refactoring moves dbstore configurations into the database itself, stored as a "storetable" in instance parameters, providing a more flexible and maintainable solution.

## Problem

**Current Issues:**
- XML-based configuration requires file system access
- Configuration changes often need server restart
- Difficult to manage programmatically
- Deployment-specific configs complicate version control
- Not container/cloud-friendly (requires volume mounts for config files)
- Coupling between code and deployment configuration

## Goals

1. Move dbstore configuration from XML to database
2. Enable dynamic configuration updates
3. Provide programmatic configuration API
4. Maintain backward compatibility with existing XML configs
5. Improve deployment and container support
6. Create foundation for multidomain workspace feature

## Technical Implementation

### New Components

**Storetable Module** (`packages/multidb/lib/storetable.py`)
- Core storetable functionality
- Serialization/deserialization utilities
- Configuration validation
- Migration helpers

### Modified Components

**Database Layer** (`gnrsql.py`)
- Store initialization from storetable
- Connection parameter resolution
- Store activation/deactivation
- Fallback to XML for backward compatibility

**Application Layer** (`gnrapp.py`)
- Storetable loading at startup
- Store configuration API
- Integration with multidb package

**Adapters** (`adapters/_gnrbaseadapter.py`)
- Unified `raw_fetch()` API
- Improved parameter handling
- Better error reporting

**Utilities** (`gnrdict.py`)
- UnionDict for merging store configurations
- Configuration override support

## Data Model

Storetable stored as application preference:
```
Location: application preferences, package='multidb', key='storetable'
Format: Bag structure with store configurations
Schema: Each store has host, database, user, password, port, implementation
```

## Key Features

- **Dynamic Updates**: Configuration changes without server restart (in most cases)
- **Programmatic Access**: Full API for reading/writing store configs
- **Backward Compatible**: XML configs still supported during migration
- **Migration Tools**: Automated migration from XML to storetable
- **Security**: Support for encrypted password storage
- **Cloud Native**: No file system dependencies for configuration

## Dependencies

**Required:**
- Multidb package
- Core Bag/preference system

**Enables:**
- Multidomain workspace feature (future dependency)

## Acceptance Criteria

- [ ] Storetable module implements core functionality
- [ ] Database layer reads from storetable correctly
- [ ] Connection parameters resolved from storetable
- [ ] Backward compatibility with XML maintained
- [ ] Migration tool converts XML to storetable
- [ ] Programmatic API for store management working
- [ ] All existing multidb tests pass
- [ ] New tests for storetable functionality added
- [ ] Documentation complete

## Implementation Checklist

### Phase 1: Core Infrastructure
- [x] Create storetable module
- [x] Implement storetable serialization
- [x] Add UnionDict utility to gnrdict
- [x] Update gnrsql.py store initialization
- [x] Modify get_connection_params()

### Phase 2: Application Integration
- [x] Update gnrapp.py loadDbStores()
- [x] Add store configuration API
- [x] Integrate with multidb package
- [x] Update adapter base class

### Phase 3: Migration & Compatibility
- [x] XML fallback support
- [ ] Migration tool from XML to storetable
- [ ] Migration documentation
- [ ] Backward compatibility tests

### Phase 4: Testing & Documentation
- [x] Unit tests for storetable
- [x] Integration tests for store loading
- [ ] Migration tests
- [x] Documentation (DBSTORES_STORETABLE_REFACTOR.md)
- [ ] API documentation
- [ ] Migration guide

## Testing Requirements

### Unit Tests
- Storetable serialization/deserialization
- Store configuration validation
- Connection parameter resolution
- UnionDict merge behavior

### Integration Tests
- Store loading from database
- Multi-store operations
- Store activation/deactivation
- Fallback to XML when storetable missing

### Migration Tests
- XML to storetable conversion
- Verification of migrated data
- Rollback scenarios

### Performance Tests
- Startup time impact
- Store connection pooling
- Configuration cache effectiveness

## Migration Path

### For Existing Installations

1. **Preparation Phase**
   - Backup existing dbstores.xml
   - Test in staging environment
   - Document current store configurations

2. **Migration Phase**
   - Run migration tool to populate storetable
   - Verify storetable contents
   - Test store connections
   - Keep XML as backup during transition

3. **Validation Phase**
   - Run full test suite
   - Verify all stores accessible
   - Test store switching
   - Monitor logs for issues

4. **Cleanup Phase** (optional)
   - Archive or remove XML files
   - Update deployment documentation
   - Train team on new configuration method

### For New Installations

- Configure stores directly via storetable
- No XML files needed
- Web UI for store administration (future enhancement)

## Breaking Changes

**None** - Feature is fully backward compatible.

- XML configurations continue to work
- Existing `db.dbstores` API unchanged
- No application code changes required

## Performance Impact

- **Startup**: +1 database query (storetable load)
- **Runtime**: No change - stores cached as before
- **Memory**: Negligible - storetable is small
- **Overall**: No measurable impact

## Security Considerations

### Password Management
- Support for encrypted passwords in storetable
- Integration with secret management systems recommended
- Separate credentials per environment best practice

### Access Control
- Storetable stored in system preferences
- Controlled by application-level permissions
- Consider role-based access for store configuration

### Audit Trail
- Configuration changes logged
- Consider versioning for storetable updates
- Track who modified store configurations

## Documentation

- [x] Feature overview (DBSTORES_STORETABLE_REFACTOR.md)
- [x] Architecture documentation
- [x] API reference
- [x] Migration guide
- [ ] Admin guide
- [ ] Video tutorial (optional)

## Timeline

**Phase 1: Core Implementation** (Completed)
- Storetable module
- Database layer integration
- Basic functionality

**Phase 2: Testing & Polish** (Current)
- Comprehensive testing
- Edge case handling
- Performance validation

**Phase 3: Migration Tools**
- XML to storetable migration script
- Validation tools
- Documentation

**Phase 4: Release**
- Final testing
- Documentation complete
- Release notes
- Team training

## Related Work

- **Multidomain Workspace**: Will build on this foundation
- **Container Deployment**: Enables better cloud/container support
- **Admin UI**: Future enhancement for web-based store management

## Success Metrics

- Zero regressions in multidb functionality
- Successful migration of at least 5 production instances
- Positive feedback from operations team
- Reduction in configuration-related support tickets

## Rollback Plan

If issues arise:
1. XML fallback is automatic if storetable not found
2. Can disable storetable loading via config flag
3. No database schema changes - safe to revert code
4. XML configs preserved during migration

## Notes

- Implementation started Sept 9, 2025
- Core work completed by Sept 25, 2025
- Builds foundation for multidomain feature
- No breaking changes - fully backward compatible

## Open Questions

- [ ] Should we provide automatic XML→storetable migration on first startup?
- [ ] Do we need storetable versioning for updates?
- [ ] Should there be a web UI for store administration?
- [ ] How to handle store passwords in version control?

## Resources

- Documentation: `DBSTORES_STORETABLE_REFACTOR.md`
- Code: `packages/multidb/lib/storetable.py`
- Tests: `tests/sql/test_gnrsql.py`
