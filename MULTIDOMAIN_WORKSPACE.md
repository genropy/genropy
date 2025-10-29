# Multidomain Workspace Feature

## Overview

This feature introduces a **multidomain mode** for Genropy's multidb (multi-tenant) system that provides strong tenant separation, similar to independent workspaces. Each domain functions as an isolated environment with separate preferences, users, and most database tables.

## Key Concepts

### What is Multidomain?

Multidomain is an enhanced multi-tenancy mode where tenants (domains) are much more separated than in standard multidb mode:

- **Standard multidb**: Tenants share most configuration and users, with data separation mainly in business tables
- **Multidomain mode**: Tenants are almost completely isolated, like separate applications sharing the same codebase

Think of it as a "workspace" model where each domain is an independent environment.

### The `_main_` Domain

The framework introduces a special domain called `_main_` which serves as:
- The root/default domain
- The primary domain for shared resources
- The fallback when no specific domain is selected

## Architecture

### Core Components

1. **GnrDomainHandler** (`gnrwsgisite.py:167-186`)
   - Manages the collection of domains
   - Handles domain registration and lookup
   - Automatically discovers domains from dbstores configuration

2. **GnrDomainProxy** (`gnrwsgisite.py:147-164`)
   - Represents a single domain
   - Provides access to domain-specific register
   - Stores domain attributes and configuration

3. **Domain Properties**
   - `site.rootDomain`: Always `_main_` - the default domain
   - `site.currentDomain`: The active domain for current request/context
   - `site.domains`: The domain handler collection

### Database Integration

Multidomain mode works in conjunction with the dbstores refactoring:

- Each domain can have its own database store (via dbstores)
- Tables can be domain-specific or shared
- Preferences are separated by domain
- Users can be isolated per domain (optional)

### Key Files Modified

**Core Framework:**
- `gnrpy/gnr/web/gnrwsgisite.py` - Domain handler infrastructure
- `gnrpy/gnr/web/gnrwebpage.py` - Domain context in pages
- `gnrpy/gnr/web/gnrwebpage_proxy/connection.py` - Domain-aware connections
- `gnrpy/gnr/sql/gnrsql.py` - Database domain support
- `gnrpy/gnr/sql/gnrsqltable.py` - Table domain awareness
- `gnrpy/gnr/app/gnrapp.py` - App-level domain logic

**Packages:**
- `projects/gnrcore/packages/adm/model/preference.py` - Domain-separated preferences
- `projects/gnrcore/packages/adm/resources/frameindex.js` - Client-side domain handling
- `projects/gnrcore/packages/multidb/main.py` - Multidb package integration
- `projects/gnrcore/packages/multidb/resources/public.py` - Public access handling

## Usage

### Configuration

Enable multidomain mode in your instance configuration:

```python
# In instanceconfig
app.config['multidomain'] = True
```

### Domain Selection

The framework automatically handles domain selection based on:
- Request hostname/subdomain
- URL routing
- Cookie-based domain preference
- Explicit domain switching

### Accessing Current Domain

```python
# In page code
current_domain = self.site.currentDomain

# Check if using main domain
if current_domain == self.site.rootDomain:
    # Main domain logic
    pass

# Access domain-specific store
domain_proxy = self.site.domains[current_domain]
```

### Domain-Separated Preferences

Preferences automatically respect domain boundaries:

```python
# Preferences are stored per domain
pref_value = self.db.application.getPreference('my_pref', pkg='mypackage')
# Returns different values for different domains
```

## Implementation Details

### Cookie Path Handling

Multidomain mode includes improved cookie path handling to ensure cookies are properly scoped to their domains, preventing cross-domain cookie leakage.

### Public Resources

Public resources (non-authenticated pages) can be configured to work across domains or be domain-specific through the `multidb/resources/public.py` configuration.

### Table Master Index

The table master index system has been enhanced to work with multidomain, using new algorithms for efficiently routing queries to the correct domain's database.

### Database Connection Management

Connections are managed per-domain, with the connection proxy system automatically selecting the correct database based on the current domain context.

## Migration Path

For existing multidb installations wanting to enable multidomain:

1. Ensure dbstores refactoring is applied (storetable-based configuration)
2. Enable `multidomain` flag in instance configuration
3. Configure domain-specific preferences if needed
4. Test domain isolation thoroughly
5. Update any custom code that assumes single-tenant behavior

## Benefits

- **Strong tenant isolation**: Enhanced security and data separation
- **Independent configuration**: Each domain can have distinct settings
- **Flexible user management**: Option to separate user bases per domain
- **Workspace-like experience**: Tenants feel like separate applications
- **Scalable architecture**: Clean foundation for multi-domain deployments

## Dependencies

This feature builds upon and requires:
- **DBStores Storetable Refactoring**: The new storetable-based dbstore configuration system
- **Multidb Package**: The core multi-database support package

## Testing

Key areas to test:
- Domain switching and context preservation
- Preference isolation between domains
- Database connection routing
- Cookie scoping and security
- Public resource access
- User authentication across domains

## Future Enhancements

Possible future improvements:
- Cross-domain data sharing APIs
- Domain-specific theming
- Enhanced domain administration UI
- Domain-level analytics and monitoring
- Migration tools between domains
