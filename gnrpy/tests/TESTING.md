# Testing Guide for genro-storage Integration

## Running Tests

### Native Storage Tests

Test the original Genropy storage implementation:

```bash
cd gnrpy
export PYTHONPATH=$PWD:$PYTHONPATH
pytest tests/core/gnrstorage_test.py -v
```

**Expected:** 46/46 tests pass

### genro-storage Wrapper Tests

Test the genro-storage wrapper for backward compatibility:

```bash
cd gnrpy
export PYTHONPATH=$PWD:$PYTHONPATH
pytest tests/core/gnrstorage_wrapper_test.py -v
```

**Expected:** 32/32 tests pass

### All Storage Tests

```bash
cd gnrpy
export PYTHONPATH=$PWD:$PYTHONPATH
pytest tests/core/gnrstorage*.py -v
```

**Expected:** 78/78 tests pass (46 native + 32 wrapper)

## Prerequisites

The wrapper tests require `genro-storage` to be installed:

```bash
# Install from local development version
pip install -e /path/to/genro-storage

# Or from GitHub
pip install git+https://github.com/genropy/genro-storage.git
```

If `genro-storage` is not installed, wrapper tests will be skipped automatically.

## Test Coverage

### Native Tests (`gnrstorage_test.py`)
- Properties: fullpath, basename, ext, size, mtime, etc.
- File operations: open, read, write, exists, isfile, isdir
- Directory operations: mkdir, children, listdir, child
- Copy/move/delete operations
- Utilities: md5hash, base64, mimetype, url
- Context managers: local_path()
- Metadata operations

### Wrapper Tests (`gnrstorage_wrapper_test.py`)
- Same API coverage as native tests
- Configuration converter tests
- Verifies 100% backward compatibility

## Troubleshooting

### ModuleNotFoundError: No module named 'gnr'

**Solution:** Set PYTHONPATH to the gnrpy directory:

```bash
export PYTHONPATH=/path/to/genropy/gnrpy:$PYTHONPATH
```

### Tests skipped: "genro-storage not installed"

**Solution:** Install genro-storage:

```bash
pip install genro-storage
```

### Permission errors when uninstalling genropy

This can happen if genropy is installed from a different path. Solution:

```bash
# Just set PYTHONPATH instead of reinstalling
export PYTHONPATH=$PWD:$PYTHONPATH
```

## CI/CD Integration

For CI/CD pipelines, add to your test script:

```yaml
# .github/workflows/test.yml
- name: Run storage tests
  run: |
    cd gnrpy
    export PYTHONPATH=$PWD:$PYTHONPATH
    pytest tests/core/gnrstorage*.py -v
```

## Development Workflow

1. Make changes to `storage_genro_adapter.py`
2. Run wrapper tests to verify compatibility:
   ```bash
   cd gnrpy && export PYTHONPATH=$PWD:$PYTHONPATH && pytest tests/core/gnrstorage_wrapper_test.py -v
   ```
3. Ensure all 32 tests pass before committing

## Test Maintenance

When adding new methods to StorageNode:

1. Add test to `gnrstorage_test.py` for native implementation
2. Add equivalent test to `gnrstorage_wrapper_test.py` for wrapper
3. Implement method in `GenroStorageNodeWrapper` class
4. Verify both test suites pass
