# Schema Selection and Staging Implementation Details

## Question 1: Schema Selection Support

### ✅ **YES, the implementation supports selecting specific schemas**

#### How it works:

1. **Specify specific schemas:**
   ```bash
   pg-sample --schema public --schema app_data --limit "*=100" --file output.sql
   ```
   This will **only** sample tables from the `public` and `app_data` schemas.

2. **Default behavior (no schema specified):**
   - If you don't specify `--schema`, it samples from **ALL schemas** in the database
   - **System schemas are automatically excluded**: `pg_catalog`, `information_schema`, `pg_toast`
   - All user-created schemas are included by default

3. **Exclude specific schemas:**
   ```bash
   pg-sample --exclude-schema logs --exclude-schema archive --limit "*=100" --file output.sql
   ```
   This samples from all schemas **except** `logs` and `archive`.

#### Code Implementation:

The schema filtering logic is in `pg_sample/schema.py`:

```python
# If schemas are specified, only include those
if schemas:
    schema_filter = f"n.nspname IN ({schema_placeholders})"
    params.extend(schemas)
# Otherwise, exclude system schemas by default
elif exclude_schemas:
    schema_filter = f"n.nspname NOT IN ({exclude_placeholders})"
    params.extend(exclude_schemas)
```

**Default excluded schemas** (hardcoded):
- `pg_catalog`
- `information_schema`  
- `pg_toast`

#### Examples:

```bash
# Sample only from 'public' schema
pg-sample --schema public --limit "*=100" --file output.sql

# Sample from multiple schemas
pg-sample --schema public --schema app --schema billing --limit "*=100" --file output.sql

# Sample from all schemas except logs and archive
pg-sample --exclude-schema logs --exclude-schema archive --limit "*=100" --file output.sql

# Default: all user schemas (system schemas auto-excluded)
pg-sample --limit "*=100" --file output.sql
```

---

## Question 2: Staging Data in Temporary Schema/Database

### ✅ **YES, the implementation supports staging data in a temporary schema**

#### Current Implementation:

The tool supports **two modes**:

1. **Direct Mode** (default for small databases):
   - Directly queries the source database
   - Writes SQL output to a file
   - All operations are read-only queries against source
   - No temporary schema needed

2. **Staging Mode** (auto-enabled for large databases, or explicitly enabled):
   - Creates a temporary schema (default: `_pg_sample`)
   - Stages sampled data in intermediate tables
   - Creates indexes for efficient FK resolution
   - Reads final data from staging tables
   - Automatically cleans up staging schema (unless `--keep` is used)

#### How Staging Mode Works:

1. **Connection**: Connects to source database
2. **Schema Creation**: Creates temporary staging schema (e.g., `_pg_sample`)
3. **First Pass**: Sample data into staging tables
4. **Index Creation**: Create indexes on staging tables for FK resolution
5. **Second Pass**: Resolve foreign key dependencies using staging tables
6. **Third Pass**: Read final data from staging tables
7. **Output Generation**: Writes SQL INSERT statements to output file
8. **Cleanup**: Drops staging schema (unless `--keep` flag is used)

#### Staging Mode Options:

- `--sample-schema` (default: `_pg_sample`) - Name of staging schema
- `--use-staging` - Explicitly enable staging mode
- `--no-staging` - Explicitly disable staging mode
- `--force` - Drop existing staging schema if it exists
- `--keep` - Preserve staging schema after completion (for debugging)

#### Auto-Detection:

Staging mode is **automatically enabled** when:
- Database has > 50 tables, OR
- Database has tables with > 5 foreign keys each

Otherwise, direct mode is used for better performance on small databases.

---

## Merits of Using a Staging Approach

### ✅ **Potential Benefits:**

1. **Performance for Complex Sampling:**
   - Could pre-compute foreign key dependencies
   - Build indexes on sampled data for faster FK resolution
   - Avoid repeated queries to source database

2. **Validation Before Export:**
   - Verify referential integrity in staging area
   - Check data quality before generating final SQL
   - Easier to debug sampling issues

3. **Incremental/Resumable Operations:**
   - Could checkpoint progress in staging schema
   - Resume interrupted operations
   - Better for very large databases

4. **Memory Efficiency:**
   - Stream data to staging tables instead of holding in memory
   - Better for databases with millions of rows

5. **Multi-Pass Sampling:**
   - First pass: sample initial rows
   - Second pass: resolve FK dependencies
   - Third pass: validate and export
   - More control over the sampling process

6. **Parallel Processing:**
   - Could sample multiple tables in parallel to staging
   - Better utilization of database resources

### ❌ **Potential Drawbacks:**

1. **Additional Complexity:**
   - Need to manage schema creation/deletion
   - More code to maintain
   - More potential failure points

2. **Requires Write Permissions:**
   - Current implementation only needs SELECT
   - Staging would require CREATE/DROP schema permissions
   - May not be possible in read-only environments

3. **Disk Space:**
   - Staging schema uses database storage
   - Could be significant for large samples
   - Need cleanup logic

4. **Transaction Management:**
   - More complex transaction handling
   - Need to handle rollback scenarios
   - Longer-running transactions

5. **Performance Overhead:**
   - Extra I/O for writing to staging tables
   - Additional queries to read from staging
   - May be slower for simple cases

6. **Concurrency Issues:**
   - Multiple runs could conflict on staging schema
   - Need locking mechanisms
   - More complex error handling

---

## Current Approach vs Staging Approach

### Current (Direct Query) Approach:

**Pros:**
- ✅ Simple and straightforward
- ✅ Read-only (no write permissions needed)
- ✅ No disk space overhead
- ✅ Fast for typical use cases
- ✅ Works in restricted environments

**Cons:**
- ❌ May be slower for very complex FK resolution
- ❌ All data held in memory during processing
- ❌ Harder to validate before export
- ❌ No checkpoint/resume capability

### Staging Approach:

**Pros:**
- ✅ Better for very large databases
- ✅ Can validate before export
- ✅ Supports checkpoint/resume
- ✅ Better memory efficiency
- ✅ More control over sampling process

**Cons:**
- ❌ Requires write permissions
- ❌ More complex implementation
- ❌ Uses database disk space
- ❌ Slower for simple cases
- ❌ More failure points

---

## Recommendation

For the **current MVP**, the direct query approach is appropriate because:

1. **Simplicity**: Easier to understand and maintain
2. **Compatibility**: Works in read-only environments
3. **Performance**: Sufficient for typical use cases (< 1GB databases)
4. **Requirements**: Meets the core requirements without extra complexity

**Staging could be added in a future version** (V1.1 or V2.0) if:
- Users need to sample very large databases (>10GB)
- Checkpoint/resume functionality is required
- More sophisticated validation is needed
- Performance becomes an issue with complex FK resolution

---

## Implementation Status Summary

| Feature | Status | Notes |
|---------|--------|-------|
| Schema selection (`--schema`) | ✅ **Implemented** | Works as documented |
| Schema exclusion (`--exclude-schema`) | ✅ **Implemented** | Works as documented |
| Default schema behavior | ✅ **Implemented** | All user schemas, excludes system schemas |
| Temporary staging schema | ✅ **Implemented** | Auto-enabled for large databases |
| Staging data | ✅ **Implemented** | Optional staging mode available |
| `--sample-schema` flag | ✅ **Implemented** | Configures staging schema name |
| `--use-staging` flag | ✅ **Implemented** | Explicitly enables staging mode |
| `--no-staging` flag | ✅ **Implemented** | Explicitly disables staging mode |
| `--force` flag | ✅ **Implemented** | Drops existing staging schema |
| `--keep` flag | ✅ **Implemented** | Preserves staging schema after completion |

