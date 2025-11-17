# Quick Start Testing Guide

## Step 1: Install the Package

```bash
pip install -e .
```

## Step 2: Set Up Test Database (Optional)

If you don't have a test database, create one:

```bash
# Create database
createdb -U postgres pg_sample_test

# Load test data
psql -U postgres -d pg_sample_test -f test_setup.sql
```

Or on Windows:
```cmd
createdb -U postgres pg_sample_test
psql -U postgres -d pg_sample_test -f test_setup.sql
```

## Step 3: Run Basic Test

### Windows:
```cmd
pg-sample --host localhost --username postgres --dbname pg_sample_test --limit "*=5" --file test_output.sql --verbose
```

### Linux/Mac:
```bash
pg-sample --host localhost --username postgres --dbname pg_sample_test --limit "*=5" --file test_output.sql --verbose
```

## Step 4: Verify Output

Check the generated SQL file:

```bash
# Linux/Mac
head -50 test_output.sql

# Windows
type test_output.sql | more
```

You should see:
- `BEGIN;` at the start
- `CREATE TABLE` statements
- `INSERT INTO` statements with data
- `ALTER TABLE` statements for constraints
- `COMMIT;` at the end

## Step 5: Test Import (Optional)

Import the generated SQL into a new database to verify it works:

```bash
# Create new database
createdb -U postgres pg_sample_test_import

# Import
psql -U postgres -d pg_sample_test_import -f test_output.sql

# Verify
psql -U postgres -d pg_sample_test_import -c "SELECT COUNT(*) FROM users;"
```

## Common Test Scenarios

### Test 1: Basic Sampling
```bash
pg-sample --host localhost --username postgres --dbname pg_sample_test --limit "*=10" --file test1.sql
```

### Test 2: Custom Limits
```bash
pg-sample --host localhost --username postgres --dbname pg_sample_test --limit "users=5,orders=3,*=2" --file test2.sql
```

### Test 3: Exclude Sensitive Columns
```bash
pg-sample --host localhost --username postgres --dbname pg_sample_test --exclude-column "users.password,*.secret_key" --limit "*=5" --file test3.sql
```

### Test 4: Schema Filtering
```bash
pg-sample --host localhost --username postgres --dbname pg_sample_test --schema public --exclude-schema archive --limit "*=5" --file test4.sql
```

### Test 5: Ordered Sampling
```bash
pg-sample --host localhost --username postgres --dbname pg_sample_test --ordered --ordered-desc --limit "*=5" --file test5.sql
```

### Test 6: Data Only (No Schema)
```bash
pg-sample --host localhost --username postgres --dbname pg_sample_test --data-only --limit "*=5" --file test6.sql
```

## Automated Testing

### Run All Tests (Linux/Mac):
```bash
./run_tests.sh pg_sample_test postgres localhost
```

### Run All Tests (Windows):
```cmd
run_tests.bat pg_sample_test postgres localhost
```

### Test Import:
```bash
./test_import.sh test_basic.sql pg_sample_test_import postgres
```

## Troubleshooting

**Connection Error?**
- Check PostgreSQL is running: `pg_isready`
- Verify credentials
- Try: `--connection-uri "postgresql://user:pass@localhost:5432/dbname"`

**Permission Error?**
- Grant permissions: `GRANT SELECT ON ALL TABLES IN SCHEMA public TO your_user;`

**No Output File?**
- Check for errors in console output
- Verify database name is correct
- Check file permissions in output directory

## What to Look For

✅ **Success indicators:**
- SQL file is created
- File contains BEGIN/COMMIT
- Contains CREATE TABLE statements
- Contains INSERT statements with data
- Foreign key constraints are included
- No errors in console output

❌ **Failure indicators:**
- Connection errors
- Permission denied errors
- Empty or malformed SQL file
- Missing foreign key dependencies

## Next Steps

See `TESTING.md` for comprehensive testing scenarios and detailed verification steps.

