# Ticket: Multidomain Workspace Feature Implementation

## Summary

Implement enhanced multi-tenancy mode with strong domain separation, providing workspace-like isolation for tenants in the Genropy framework.

## Description

This feature introduces a "multidomain" mode for the multidb (multi-tenant) system that significantly strengthens tenant separation. Unlike standard multidb where tenants share most configuration, multidomain mode treats each domain as an almost-independent application with its own preferences, users, and database configuration.

## Goals

1. Provide workspace-like tenant isolation
2. Enable per-domain preferences and configuration
3. Support domain-specific database stores
4. Maintain clean separation between domain contexts
5. Ensure secure cookie and session handling across domains

## Technical Implementation

### New Components

- **GnrDomainHandler**: Manages domain collection and discovery
- **GnrDomainProxy**: Represents individual domain with its configuration
- **Root Domain (`_main_`)**: Default domain for shared resources

### Modified Components

- Enhanced site infrastructure (`gnrwsgisite.py`)
- Domain-aware database layer (`gnrsql.py`, `gnrsqltable.py`)
- Domain context in web pages (`gnrwebpage.py`)
- Preference system with domain separation
- Cookie path handling for domain isolation

## Key Features

- Automatic domain discovery from dbstores
- Request-based domain selection (hostname, routing, cookies)
- Per-domain preference storage and retrieval
- Domain-scoped database connections
- Optional per-domain user isolation
- Public resource configuration per domain

## Dependencies

**Required:**
- DBStores Storetable Refactoring (separate feature)
- Multidb package

## Acceptance Criteria

- [ ] Domain handler correctly manages multiple domains
- [ ] Domain context preserved throughout request lifecycle
- [ ] Preferences correctly isolated between domains
- [ ] Database connections route to correct domain stores
- [ ] Cookies properly scoped to prevent cross-domain leakage
- [ ] Public resources accessible according to domain config
- [ ] No regression in standard multidb (non-multidomain) mode
- [ ] Documentation complete and clear

## Testing Requirements

### Unit Tests
- Domain handler registration and lookup
- Domain context switching
- Preference isolation

### Integration Tests
- Full request cycle with domain switching
- Database connection routing
- Cookie handling across domains
- Public vs authenticated resource access

### Manual Testing
- Multi-domain deployment scenario
- User login across different domains
- Preference management per domain
- Performance under multiple active domains

## Migration Considerations

For existing multidb installations:
1. Feature is opt-in via configuration flag
2. Backward compatible with non-multidomain mode
3. Requires dbstores storetable refactoring to be applied first
4. Existing single-domain installations unaffected

## Documentation

- [x] Feature overview (MULTIDOMAIN_WORKSPACE.md)
- [x] Architecture documentation
- [x] Configuration guide
- [x] API usage examples
- [x] Migration guide

## Timeline

**Phase 1: Core Implementation** (Completed)
- Domain handler infrastructure
- Site and database integration
- Basic domain switching

**Phase 2: Polish & Testing** (Current)
- Cookie path handling refinements
- Public resource configuration
- Edge case handling
- Comprehensive testing

**Phase 3: Documentation & Release**
- Complete documentation
- Migration guides
- Release notes

## Related Work

- **DBStores Storetable Refactoring**: Must be merged first
- **Multidb Package**: Core dependency

## Notes

- The `gnrdaemonhandler_multidomain.py` file created during early development was unused and has been removed
- Actual implementation uses direct integration into `gnrwsgisite.py` and related files
- Cookie path handling had multiple iterations to get right (commits show reverts and improvements)

## Breaking Changes

None - feature is opt-in and backward compatible.

## Performance Considerations

- Domain lookup is cached in handler
- Connection pooling per domain
- Minimal overhead when multidomain disabled
- Preference queries scoped to reduce dataset size

## Security Considerations

- Cookie isolation prevents cross-domain access
- Database connection credentials per domain
- User authentication can be domain-scoped
- Public resource access configurable per domain
