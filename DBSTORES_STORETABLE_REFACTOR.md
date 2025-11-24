# DBStores Storetable Refactoring

## Overview

This refactoring modernizes the way Genropy manages database store configurations for multi-database (multidb) deployments. Instead of relying on XML configuration files, dbstore settings are now managed through a database table within the instance parameters, providing a more dynamic and maintainable approach.

**Critical for Cloud-Native Deployments:** This change is essential for containerized and Kubernetes-based deployments where file-based configuration is problematic and environment-based configuration is preferred.

## Problem Statement

### The XML Configuration Problem

**Before this refactoring:**
- DBStore configurations were stored in XML files (e.g., `dbstores.xml` in instance folder)
- Configuration required file system access and volume mounts
- Changes needed server restarts
- Difficult to manage programmatically
- Version control complexities for deployment-specific settings
- **Container/K8s Pain Points:**
  - Required persistent volumes just for configuration files
  - ConfigMaps/Secrets couldn't easily update XML structures
  - Different configs per environment needed multiple image builds or complex volume mounting
  - No way to configure stores via environment variables
  - Difficult to manage multi-tenant deployments dynamically

### The Database-First Solution

**After this refactoring:**
- DBStore configurations stored in database (storetable)
- Dynamic configuration without file system dependencies
- Programmatic configuration management via API
- Cleaner separation of code and configuration
- **Cloud-Native Benefits:**
  - Zero file system dependencies for configuration
  - Perfect for stateless containers
  - Configuration via environment variables (database connection only)
  - Dynamic tenant/store provisioning without redeployment
  - Works seamlessly with Kubernetes, Docker Compose, cloud platforms
  - Configuration is data, backed up with database

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

### 1. Cloud-Native & Container-First Architecture

**Kubernetes/Docker Advantages:**
- **Stateless Containers:** No need for persistent volumes for configuration
- **12-Factor App Compliance:** Configuration stored in environment (database connection)
- **Horizontal Scaling:** Same container image works across all environments
- **ConfigMap Independence:** Database stores config, not YAML files
- **Environment Parity:** Dev/staging/prod differ only by database connection

**Deployment Simplification:**
```yaml
# Before: Complex volume mounts for XML configs
volumes:
  - name: instance-config
    configMap:
      name: dbstores-xml  # Different per environment!

# After: Simple database connection via env vars
env:
  - name: GNR_DB_HOST
    value: "postgres.svc.cluster.local"
  - name: GNR_DB_NAME
    value: "genropy"
  # Stores configured in database, zero file mounts needed
```

### 2. Dynamic Configuration

- No server restart needed for store changes (in most cases)
- Web-based administration interface possible
- API-driven configuration management
- **Runtime tenant provisioning** - Add new stores without redeploying containers
- Perfect for SaaS multi-tenant platforms

### 3. Better Deployment Practices

- No configuration files to manage across environments
- Secrets can use proper secret management (Vault, AWS Secrets Manager, etc.)
- Container-friendly (no volume mounts for config)
- **Single source of truth** for all environments
- **Infrastructure as Code** friendly - Terraform can manage stores via API

### 4. Version Control Sanity

- Configuration is data, not code
- No merge conflicts on environment-specific configs
- Easier to maintain separate dev/staging/production setups
- **Code is environment-agnostic** - Same image everywhere
- Git repos contain code only, not deployment configs

### 5. Programmatic Access

- Easy to query and modify stores from code
- Migration scripts can update configuration
- Integration with deployment automation (CI/CD pipelines)
- **REST API ready** for external provisioning systems
- Ansible/Terraform can configure stores programmatically

### 6. Multidb Integration & Scalability

- Tighter integration with multidb package
- Foundation for multidomain workspace feature
- Cleaner abstraction layers
- **Supports thousands of tenants** without file system limits
- Database transactions ensure consistency

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

## Container/Kubernetes Deployment

### Docker Deployment

**Dockerfile approach - Zero configuration files needed:**

```dockerfile
FROM genropy/base:latest

# Only database connection needed via environment variables
ENV GNR_DB_HOST=postgres
ENV GNR_DB_NAME=genropy
ENV GNR_DB_USER=genropy
ENV GNR_DB_PASSWORD=secret

# No volume mounts for configuration!
# Stores configured in database at runtime

CMD ["gnr_serve", "myinstance"]
```

**Docker Compose example:**

```yaml
version: '3.8'
services:
  genropy-app:
    image: mycompany/genropy-app:latest
    environment:
      GNR_DB_HOST: postgres
      GNR_DB_NAME: genropy
      GNR_DB_USER: genropy
      GNR_DB_PASSWORD: ${DB_PASSWORD}
    # No volumes for configuration!
    depends_on:
      - postgres

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: genropy
      POSTGRES_USER: genropy
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data

volumes:
  postgres-data:
```

### Kubernetes Deployment

**Deployment manifest - Stateless and scalable:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: genropy-app
spec:
  replicas: 3  # Can scale horizontally!
  selector:
    matchLabels:
      app: genropy
  template:
    metadata:
      labels:
        app: genropy
    spec:
      containers:
      - name: genropy
        image: mycompany/genropy-app:v1.0
        env:
        - name: GNR_DB_HOST
          value: postgres-service.database.svc.cluster.local
        - name: GNR_DB_NAME
          value: genropy
        - name: GNR_DB_USER
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: username
        - name: GNR_DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: password
        # NO VOLUME MOUNTS FOR CONFIGURATION!
        # Stores managed in database
```

**Secret management:**

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: db-credentials
type: Opaque
data:
  username: Z2VucnB5  # base64 encoded
  password: c2VjcmV0  # base64 encoded
```

### Cloud Platform Deployments

**AWS ECS Task Definition:**

```json
{
  "family": "genropy-app",
  "containerDefinitions": [{
    "name": "genropy",
    "image": "123456789.dkr.ecr.us-east-1.amazonaws.com/genropy:latest",
    "environment": [
      {"name": "GNR_DB_HOST", "value": "genropy.cluster-xxx.rds.amazonaws.com"},
      {"name": "GNR_DB_NAME", "value": "genropy"}
    ],
    "secrets": [
      {"name": "GNR_DB_USER", "valueFrom": "arn:aws:secretsmanager:..."},
      {"name": "GNR_DB_PASSWORD", "valueFrom": "arn:aws:secretsmanager:..."}
    ]
  }]
}
```

**Google Cloud Run:**

```bash
gcloud run deploy genropy-app \
  --image gcr.io/project/genropy:latest \
  --set-env-vars GNR_DB_HOST=10.1.2.3 \
  --set-env-vars GNR_DB_NAME=genropy \
  --set-secrets GNR_DB_USER=db-user:latest \
  --set-secrets GNR_DB_PASSWORD=db-pass:latest \
  --allow-unauthenticated
```

### Dynamic Tenant Provisioning

**Add new tenant via API (no container restart needed):**

```python
# In running container or via management API
from gnr.app.gnrapp import GnrApp

app = GnrApp('myinstance')
db = app.db

# Add new tenant store
storetable = db.application.getPreference('storetable', pkg='multidb')
storetable.setItem('tenant_newclient', None,
                   dbstore='tenant_newclient',
                   dbtemplate='standard',
                   preferences=None)
db.application.setPreference('storetable', storetable, pkg='multidb')
db.commit()

# Activate the store (creates database, syncs schema)
store_table = db.table('multidb.dbstore')
store_record = store_table.record(dbstore='tenant_newclient').output('dict')
store_table.multidb_activateDbstore(store_record)

# New tenant is live! No container restart, no file changes.
```

### CI/CD Integration

**GitLab CI example:**

```yaml
deploy:
  stage: deploy
  script:
    # Same image for all environments!
    - docker build -t genropy-app:${CI_COMMIT_SHA} .
    - docker tag genropy-app:${CI_COMMIT_SHA} genropy-app:latest

    # Deploy to Kubernetes
    - kubectl set image deployment/genropy genropy=genropy-app:${CI_COMMIT_SHA}

    # Configuration is in database, not in image or config files!
    # Different environments just point to different databases
```

### Infrastructure as Code

**Terraform example for store provisioning:**

```hcl
resource "null_resource" "genropy_tenant" {
  for_each = var.tenants

  provisioner "local-exec" {
    command = <<EOF
      curl -X POST https://api.myapp.com/admin/tenants \
        -H "Authorization: Bearer ${var.admin_token}" \
        -d '{"tenant_id": "${each.key}", "template": "${each.value.template}"}'
    EOF
  }
}
```

### Advantages Summary

**Before (XML config):**
```
❌ Persistent volume for config files
❌ Different ConfigMap per environment
❌ Can't scale horizontally with different configs
❌ Manual file editing for new tenants
❌ Image rebuild or volume remount for config changes
```

**After (Database config):**
```
✅ Zero persistent volumes for configuration
✅ Single image across all environments
✅ Horizontal scaling with identical configs
✅ API-driven tenant provisioning
✅ Configuration via environment variables only
✅ True 12-factor app compliance
```

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
