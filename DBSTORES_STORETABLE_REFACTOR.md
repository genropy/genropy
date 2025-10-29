# DBStores Storetable Refactoring

## Overview

This refactoring modernizes the way Genropy manages database store configurations for multi-database (multidb) deployments. Instead of relying on XML configuration files, dbstore settings are now managed through a database table within the instance parameters, providing a more dynamic and maintainable approach.

## Problem Statement

**Before this refactoring:**
- DBStore configurations were stored in XML files (e.g., `dbstores.xml`)
- Configuration required file system access
- Changes needed server restarts
- Difficult to manage programmatically
- Version control complexities for deployment-specific settings

**After this refactoring:**
- DBStore configurations stored in database (storetable)
- Dynamic configuration without file changes
- Programmatic configuration management
- Cleaner separation of code and configuration
- Better support for cloud/container deployments

## Architecture Changes

### Core Components

#### 1. Storetable (`packages/multidb/lib/storetable.py`)

New module providing the core storetable functionality:

```python
# Key functions:
- getStoreTable(db): Retrieve storetable from database
- saveStoreTable(db, storetable): Save storetable configuration
- storeTableToDict(storetable): Convert storetable to dictionary format
```

The storetable is stored as a Bag structure in the instance parameters, making it easily serializable and queryable.

#### 2. Database Layer Integration

**gnrsql.py** - Enhanced store management:
- `initStores()`: Initialize stores from storetable instead of XML
- `get_connection_params()`: Retrieve connection parameters from storetable
- `dbstores` property: Access to configured database stores
- `auxstores` property: Additional auxiliary stores

**gnrapp.py** - Application-level changes:
- `loadDbStores()`: Load stores from storetable at startup
- `getDbStoreConfig()`: Retrieve specific store configuration
- Integration with multidb package initialization

#### 3. Adapter Improvements

**gnrbaseadapter.py** - Raw fetch API:
- Unified `raw_fetch()` method for adapters
- Cleaner parameter handling
- Better error reporting

### Data Structure

Storetable structure in database:
```xml
<stores>
    <store code="store1"
           host="localhost"
           database="mydb1"
           user="dbuser"
           password="encrypted_pass"
           port="5432"
           implementation="postgres"/>
    <store code="store2" .../>
</stores>
```

Accessed programmatically:
```python
storetable = db.application.getPreference('storetable', pkg='multidb')
store_config = storetable['store1']
```

## Key Benefits

1. **Dynamic Configuration**
   - No server restart needed for store changes (in most cases)
   - Web-based administration interface possible
   - API-driven configuration management

2. **Better Deployment**
   - No configuration files to manage across environments
   - Secrets can use proper secret management
   - Container-friendly (no volume mounts for config)

3. **Version Control**
   - Configuration is data, not code
   - No merge conflicts on environment-specific configs
   - Easier to maintain separate dev/staging/production setups

4. **Programmatic Access**
   - Easy to query and modify stores from code
   - Migration scripts can update configuration
   - Integration with deployment automation

5. **Multidb Integration**
   - Tighter integration with multidb package
   - Foundation for multidomain workspace feature
   - Cleaner abstraction layers

## Migration Guide

### For Existing Installations

1. **Backup Current Configuration**
   ```bash
   # Backup your dbstores.xml
   cp instanceconfig/dbstores.xml instanceconfig/dbstores.xml.backup
   ```

2. **Run Migration**
   ```bash
   # Migration tool will read XML and populate storetable
   gnr_migrate_dbstores --instance myinstance
   ```

3. **Verify**
   ```python
   # In gnrdbsetup or Python shell
   db = app.db
   storetable = db.application.getPreference('storetable', pkg='multidb')
   print(storetable)
   ```

4. **Remove XML** (optional, after verification)
   ```bash
   # Once confirmed working, can remove old XML
   mv instanceconfig/dbstores.xml instanceconfig/dbstores.xml.old
   ```

### For New Installations

No migration needed - configure stores directly in database:

```python
# In initialization script or admin interface
storetable = Bag()
storetable.setItem('mystore', None,
                   host='localhost',
                   database='mydb',
                   user='dbuser',
                   password='secret',
                   implementation='postgres')
db.application.setPreference('storetable', storetable, pkg='multidb')
db.commit()
```

## API Reference

### Reading Store Configuration

```python
# Get all stores
storetable = db.application.getPreference('storetable', pkg='multidb')

# Get specific store
store_config = storetable['storename']

# Access store properties
host = store_config.attr['host']
database = store_config.attr['database']
```

### Modifying Store Configuration

```python
# Add new store
storetable = db.application.getPreference('storetable', pkg='multidb')
storetable.setItem('newstore', None,
                   host='dbhost',
                   database='dbname',
                   user='dbuser',
                   password='dbpass',
                   implementation='postgres')
db.application.setPreference('storetable', storetable, pkg='multidb')
db.commit()

# Modify existing store
store = storetable['existingstore']
store.attr['host'] = 'newhost'
db.application.setPreference('storetable', storetable, pkg='multidb')
db.commit()
```

### Programmatic Store Access

```python
# In application code
db = self.db

# Connect to specific store
with db.stores['storename'] as store_db:
    result = store_db.query('SELECT * FROM mytable').fetch()

# Check if store exists
if 'storename' in db.dbstores:
    # Store is configured
    pass
```

## Files Modified

### Core Framework
- `gnrpy/gnr/sql/gnrsql.py` - Store initialization and connection management
- `gnrpy/gnr/sql/adapters/_gnrbaseadapter.py` - Adapter improvements
- `gnrpy/gnr/app/gnrapp.py` - Application-level store loading
- `gnrpy/gnr/core/gnrdict.py` - UnionDict utility for merging store configs
- `gnrpy/gnr/web/gnrwebapp.py` - Web app integration
- `gnrpy/gnr/web/gnrwsgisite.py` - Site-level store access

### Packages
- `projects/gnrcore/packages/multidb/lib/storetable.py` - New storetable module
- `projects/gnrcore/packages/multidb/main.py` - Package initialization updates

### Tests
- `gnrpy/tests/sql/test_gnrsql.py` - Updated for new store handling

## Performance Considerations

- **Startup**: Storetable loaded once at application initialization
- **Runtime**: Store connections pooled as before
- **Caching**: Store configs cached in memory
- **Database**: One additional preference query at startup

Overall performance impact is negligible - the storetable is small and cached.

## Security Considerations

### Password Storage

Store passwords should be encrypted:

```python
from gnr.core.gnrcrypto import encrypt_password

encrypted = encrypt_password('plaintext_password')
storetable.setItem('mystore', None, password=encrypted, ...)
```

### Access Control

- Storetable is stored in system preferences
- Access controlled via application permissions
- Consider separate credentials per environment
- Use secret management for production passwords

## Backward Compatibility

- **XML Config**: Legacy XML files still supported during transition
- **API**: Existing `db.dbstores` API unchanged
- **Migration**: Automatic fallback to XML if storetable not found

Applications using the standard dbstores API will work without changes.

## Testing

### Unit Tests
- Store table serialization/deserialization
- Connection parameter resolution
- Store activation and deactivation

### Integration Tests
- Multi-store database operations
- Store configuration updates
- Migration from XML to storetable
- Fallback to XML when storetable missing

### Manual Testing
- Admin UI for store management
- Store configuration via API
- Connection pooling behavior
- Error handling for missing stores

## Future Enhancements

Possible future improvements:
- Web UI for store administration
- Store health monitoring
- Connection pool statistics
- Automatic store discovery
- Store replication configuration
- Encrypted password management UI

## Dependencies

**Required:**
- Multidb package
- gnrdict.UnionDict utility

**Enables:**
- Multidomain workspace feature (builds on this)

## Breaking Changes

None - fully backward compatible with XML-based configuration.

## Troubleshooting

### Store Not Found

```python
# Check if storetable exists
storetable = db.application.getPreference('storetable', pkg='multidb')
if not storetable:
    print("Storetable not configured, falling back to XML")
```

### Migration Issues

```bash
# Re-run migration with verbose output
gnr_migrate_dbstores --instance myinstance --verbose

# Check logs for errors
tail -f instance/data/logs/site.log
```

### Connection Failures

```python
# Verify store configuration
store_config = db.dbstores['storename']
print(f"Host: {store_config.get('host')}")
print(f"Database: {store_config.get('database')}")

# Test connection manually
import psycopg2
conn = psycopg2.connect(
    host=store_config['host'],
    database=store_config['database'],
    user=store_config['user'],
    password=store_config['password']
)
```
