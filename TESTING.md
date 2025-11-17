# Testing Guide for PostgreSQL Database Sampling Utility

## Prerequisites

1. **Install the package:**
   ```bash
   pip install -e .
   ```

2. **Ensure you have PostgreSQL installed and running**

3. **Create a test database** (or use an existing one)

## Quick Start Testing

### 1. Basic Connection Test

Test that the tool can connect to your database:

```bash
pg-sample --host localhost --username postgres --dbname postgres --dry-run
```

Expected: Should connect and show what would be sampled (though dry-run is not fully implemented yet).

### 2. Simple Sampling Test

Sample a small number of rows from all tables:

```bash
pg-sample --host localhost --username postgres --dbname postgres --limit "*=10" --file test_sample.sql
```

Expected: Creates `test_sample.sql` with schema and 10 rows per table.

### 3. Verify Output

Check the generated SQL file:

```bash
cat test_sample.sql
```

Expected: Should see:
- `BEGIN;` transaction wrapper
- `CREATE TABLE` statements
- `INSERT` statements with data
- `ALTER TABLE` statements for constraints
- `COMMIT;` at the end

## Comprehensive Test Scenarios

### Test 1: Basic Sampling with Default Limits

```bash
pg-sample \
  --host localhost \
  --username postgres \
  --dbname your_database \
  --file output_basic.sql \
  --verbose
```

**What to verify:**
- SQL file is created
- Contains schema definitions
- Contains INSERT statements
- All foreign key constraints are satisfied

### Test 2: Custom Row Limits

```bash
pg-sample \
  --host localhost \
  --username postgres \
  --dbname your_database \
  --limit "users=100,orders=50,*=10" \
  --file output_custom.sql \
  --verbose
```

**What to verify:**
- Users table has ~100 rows
- Orders table has ~50 rows
- Other tables have ~10 rows
- Foreign key relationships are maintained

### Test 3: Column Exclusion

```bash
pg-sample \
  --host localhost \
  --username postgres \
  --dbname your_database \
  --exclude-column "users.password,*.secret_key" \
  --file output_excluded.sql \
  --verbose
```

**What to verify:**
- Excluded columns appear in schema but have NULL values in INSERT statements
- No sensitive data in output

### Test 4: Schema Filtering

```bash
pg-sample \
  --host localhost \
  --username postgres \
  --dbname your_database \
  --schema public \
  --exclude-schema archive \
  --file output_filtered.sql \
  --verbose
```

**What to verify:**
- Only public schema tables are included
- Archive schema tables are excluded

### Test 5: Deterministic Ordering

```bash
pg-sample \
  --host localhost \
  --username postgres \
  --dbname your_database \
  --ordered \
  --ordered-desc \
  --limit "*=20" \
  --file output_ordered.sql \
  --verbose
```

**What to verify:**
- Rows are ordered by primary key (descending)
- Same rows selected on repeated runs (when using same ordering)

### Test 6: Random Sampling

```bash
pg-sample \
  --host localhost \
  --username postgres \
  --dbname your_database \
  --random \
  --limit "*=20" \
  --file output_random.sql \
  --verbose
```

**What to verify:**
- Different rows selected on each run
- Still maintains referential integrity

### Test 7: Data-Only Export

```bash
pg-sample \
  --host localhost \
  --username postgres \
  --dbname your_database \
  --data-only \
  --limit "*=10" \
  --file output_data_only.sql \
  --verbose
```

**What to verify:**
- Only INSERT statements (no CREATE TABLE)
- No schema definitions

### Test 8: Import and Verify

After generating a sample, test importing it:

```bash
# Create a new test database
createdb -U postgres test_sample_db

# Import the sample
psql -U postgres -d test_sample_db -f output_basic.sql

# Verify foreign key constraints
psql -U postgres -d test_sample_db -c "
SELECT 
    conname AS constraint_name,
    conrelid::regclass AS table_name,
    confrelid::regclass AS referenced_table
FROM pg_constraint
WHERE contype = 'f';
"
```

**What to verify:**
- Import succeeds without errors
- All foreign key constraints are valid
- Data relationships are intact

### Test 9: Audit Trail

```bash
pg-sample \
  --host localhost \
  --username postgres \
  --dbname your_database \
  --limit "*=10" \
  --file output.sql \
  --audit-file audit.json \
  --verbose
```

**What to verify:**
- `audit.json` is created
- Contains table names and row counts
- Contains timestamp and connection info

### Test 10: Logging Levels

Test different log levels:

```bash
# INFO level (default)
pg-sample --host localhost --username postgres --dbname your_database --limit "*=5" --log-level INFO

# DEBUG level (more verbose)
pg-sample --host localhost --username postgres --dbname your_database --limit "*=5" --log-level DEBUG

# Log to file
pg-sample --host localhost --username postgres --dbname your_database --limit "*=5" --log-file sample.log
```

## Testing with a Sample Database

If you don't have a test database, you can create one with sample data:

```sql
-- Create test database
CREATE DATABASE test_sample;

-- Connect to test_sample and run:
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    total DECIMAL(10,2),
    status VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id),
    product_name VARCHAR(100),
    quantity INTEGER,
    price DECIMAL(10,2)
);

-- Insert sample data
INSERT INTO users (username, email) VALUES
    ('alice', 'alice@example.com'),
    ('bob', 'bob@example.com'),
    ('charlie', 'charlie@example.com');

INSERT INTO orders (user_id, total, status) VALUES
    (1, 99.99, 'completed'),
    (1, 49.99, 'pending'),
    (2, 149.99, 'completed');

INSERT INTO order_items (order_id, product_name, quantity, price) VALUES
    (1, 'Widget A', 2, 49.99),
    (2, 'Widget B', 1, 49.99),
    (3, 'Widget C', 3, 49.99);
```

Then test with:

```bash
pg-sample --host localhost --username postgres --dbname test_sample --limit "*=2" --file test_output.sql --verbose
```

## Troubleshooting

### Connection Issues

If you get connection errors:
- Check PostgreSQL is running: `pg_isready`
- Verify credentials
- Check `pg_hba.conf` allows your connection method
- Try using connection URI: `--connection-uri "postgresql://user:pass@localhost:5432/dbname"`

### Permission Issues

If you get permission errors:
- Ensure user has SELECT privileges on tables
- Ensure user has USAGE privilege on schemas
- Check: `GRANT SELECT ON ALL TABLES IN SCHEMA public TO your_user;`

### Output Issues

If SQL output has errors:
- Check for unsupported data types
- Verify all foreign key dependencies are included
- Check for circular dependencies (should be handled automatically)

## Expected Behavior

✅ **Should work:**
- Sampling tables with foreign keys
- Handling circular dependencies
- Excluding columns (replaced with NULL)
- Pattern matching for limits and exclusions
- Generating valid SQL output

⚠️ **Known limitations:**
- Very large tables (>100M rows) may be slow
- Streaming for very large tables is not yet implemented (deferred to future version)

## Performance Testing

For performance testing with larger databases:

```bash
time pg-sample \
  --host localhost \
  --username postgres \
  --dbname large_database \
  --limit "*=1000" \
  --file large_sample.sql \
  --verbose
```

Monitor:
- Execution time
- Memory usage
- Database connection time
- Output file size

