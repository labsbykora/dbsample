# Migration Guide: v1.x → v2.0.0

## Overview

Version 2.0.0 is a **major release** with breaking changes due to project renaming from `pg-sample` to `dbsample`. This guide will help you migrate from v1.x to v2.0.0.

## Breaking Changes

### 1. Package Name Change
- **Old**: `pg-sample`
- **New**: `dbsample`

### 2. Command Name Change
- **Old**: `pg-sample`
- **New**: `dbsample`

### 3. Default Staging Schema Change
- **Old**: `_pg_sample`
- **New**: `_dbsample`

### 4. Python Import Paths
- **Old**: `from pg_sample.*`
- **New**: `from dbsample.*`

## Migration Steps

### Step 1: Uninstall Old Package

```bash
pip uninstall pg-sample
```

### Step 2: Install New Package

```bash
pip install dbsample
```

Or if installing from source:
```bash
pip install -e .
```

### Step 3: Update Scripts and Commands

Replace all occurrences of `pg-sample` with `dbsample` in:
- Shell scripts
- Batch files
- CI/CD pipelines
- Documentation
- Any automation scripts

**Before:**
```bash
pg-sample --host localhost --dbname mydb --limit "*=100"
```

**After:**
```bash
dbsample --host localhost --dbname mydb --limit "*=100"
```

### Step 4: Update Python Code (if applicable)

If you have Python code that imports the package:

**Before:**
```python
from pg_sample.cli import main
from pg_sample.sampling import SamplingEngine
```

**After:**
```python
from dbsample.cli import main
from dbsample.sampling import SamplingEngine
```

### Step 5: Clean Up Old Staging Schemas (Optional)

If you have existing staging schemas named `_pg_sample` in your databases, you can clean them up:

```sql
-- Check for old staging schemas
SELECT schema_name 
FROM information_schema.schemata 
WHERE schema_name = '_pg_sample';

-- Drop if found
DROP SCHEMA IF EXISTS _pg_sample CASCADE;
```

**Note**: The new version will use `_dbsample` by default, so old `_pg_sample` schemas won't interfere unless you explicitly reference them with `--sample-schema _pg_sample`.

## What Stayed the Same

✅ **No changes needed for:**
- Configuration files (JSON/YAML format unchanged)
- Command-line options (except command name)
- Output format
- All functionality
- Database connection parameters
- Sampling logic and behavior

## Verification

After migration, verify the installation:

```bash
# Check version
dbsample --version

# Test help command
dbsample --help

# Run a test
dbsample --host localhost --dbname testdb --dry-run
```

## Rollback (if needed)

If you need to rollback to v1.x:

```bash
pip uninstall dbsample
pip install pg-sample==1.2.0
```

**Note**: You'll need to update scripts back to `pg-sample` and may need to clean up `_dbsample` staging schemas.

## Questions?

- See [CHANGELOG.md](CHANGELOG.md) for complete change history
- See [README.md](README.md) for usage documentation
- See [USAGE_GUIDE.md](USAGE_GUIDE.md) for detailed usage examples

