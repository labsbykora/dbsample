# Usage Guide - Running dbsample Against Real Databases

## Prerequisites

1. **Install the package:**
   ```bash
   pip install -e .
   ```

2. **Ensure you have:**
   - PostgreSQL client tools installed
   - Network access to your PostgreSQL server
   - Appropriate database credentials

## Basic Usage

### 1. Simple Connection (Using Environment Variables)

Set PostgreSQL environment variables (optional but convenient):

**Windows (PowerShell):**
```powershell
$env:PGHOST="your-server.com"
$env:PGPORT="5432"
$env:PGUSER="your_username"
$env:PGDATABASE="your_database"
```

**Windows (CMD):**
```cmd
set PGHOST=your-server.com
set PGPORT=5432
set PGUSER=your_username
set PGDATABASE=your_database
```

**Linux/Mac:**
```bash
export PGHOST=your-server.com
export PGPORT=5432
export PGUSER=your_username
export PGDATABASE=your_database
```

Then run:
```bash
dbsample --limit "*=100" --file sample.sql
```

### 2. Explicit Connection Parameters

**Basic connection:**
```bash
dbsample \
  --host your-server.com \
  --port 5432 \
  --username your_username \
  --dbname your_database \
  --limit "*=100" \
  --file sample.sql
```

**With password prompt:**
```bash
dbsample \
  --host your-server.com \
  --username your_username \
  --dbname your_database \
  --limit "*=100" \
  --file sample.sql
# Password will be prompted if not in PGPASSWORD or .pgpass
```

### 3. Connection URI (Recommended for Complex Setups)

```bash
dbsample \
  --connection-uri "postgresql://username:password@host:port/database" \
  --limit "*=100" \
  --file sample.sql
```

Or with SSL:
```bash
dbsample \
  --connection-uri "postgresql://username:password@host:port/database?sslmode=require" \
  --limit "*=100" \
  --file sample.sql
```

### 4. Using .pgpass File (Most Secure)

Create `~/.pgpass` (Linux/Mac) or `%APPDATA%\postgresql\pgpass.conf` (Windows):

```
hostname:port:database:username:password
```

Example:
```
production-db.example.com:5432:mydb:myuser:mypassword
localhost:5432:testdb:postgres:secret
```

Set permissions (Linux/Mac only):
```bash
chmod 600 ~/.pgpass
```

Then run without password:
```bash
dbsample --host production-db.example.com --username myuser --dbname mydb --limit "*=100" --file sample.sql
```

## Common Use Cases

### Use Case 1: Create Development Sample from Production

**Scenario:** You want a small sample of production data for local development.

```bash
dbsample \
  --host production-db.example.com \
  --username readonly_user \
  --dbname production_db \
  --limit "*=1000" \
  --exclude-column "users.password,users.email,*.api_key,*.secret" \
  --exclude-schema audit_logs \
  --file dev_sample.sql \
  --verbose
```

**What this does:**
- Samples 1000 rows per table
- Excludes sensitive columns (passwords, API keys)
- Excludes audit log schema
- Creates `dev_sample.sql` for import

### Use Case 2: Sample Specific Tables with Custom Limits

**Scenario:** You need more data from important tables, less from others.

```bash
dbsample \
  --host your-server.com \
  --username your_user \
  --dbname your_db \
  --limit "users=10000,orders=5000,products=2000,order_items=10000,*=100" \
  --file important_tables_sample.sql \
  --verbose
```

**What this does:**
- 10,000 rows from `users` table
- 5,000 rows from `orders` table
- 2,000 rows from `products` table
- 10,000 rows from `order_items` table
- 100 rows from all other tables
- Automatically includes foreign key dependencies

### Use Case 3: Percentage-Based Sampling

**Scenario:** You want 10% of data from large tables.

```bash
dbsample \
  --host your-server.com \
  --username your_user \
  --dbname your_db \
  --limit "large_table=10%,medium_table=5%,*=1%" \
  --file percentage_sample.sql \
  --verbose
```

### Use Case 4: Conditional Sampling (Active Records Only)

**Scenario:** You only want active/current records.

```bash
dbsample \
  --host your-server.com \
  --username your_user \
  --dbname your_db \
  --limit "users=status='active',orders=status!='cancelled',*=100" \
  --file active_records.sql \
  --verbose
```

### Use Case 5: Schema-Specific Sampling

**Scenario:** You only want data from specific schemas.

```bash
dbsample \
  --host your-server.com \
  --username your_user \
  --dbname your_db \
  --schema public \
  --schema app_data \
  --exclude-schema logs \
  --exclude-schema archive \
  --limit "*=500" \
  --file main_schemas.sql \
  --verbose
```

### Use Case 5b: Excluding Specific Tables with Patterns

**Scenario:** You want to exclude specific tables or groups of tables using patterns.

```bash
dbsample \
  --host your-server.com \
  --username your_user \
  --dbname your_db \
  --exclude-table "temp_*" \
  --exclude-table "*_backup" \
  --exclude-table "audit.*_log" \
  --limit "*=1000" \
  --file sample.sql \
  --verbose
```

**What this does:**
- Excludes all tables starting with `temp_`
- Excludes all tables ending with `_backup`
- Excludes all tables in `audit` schema ending with `_log`
- Samples remaining tables with 1000 rows each

### Use Case 6: Deterministic Sampling (Reproducible)

**Scenario:** You want the same sample every time (for testing).

```bash
dbsample \
  --host your-server.com \
  --username your_user \
  --dbname your_db \
  --ordered \
  --ordered-desc \
  --limit "*=1000" \
  --file reproducible_sample.sql \
  --verbose
```

**What this does:**
- Orders by primary key (descending)
- Same rows selected on each run
- Useful for consistent test data

### Use Case 7: Random Sampling

**Scenario:** You want a random representative sample.

```bash
dbsample \
  --host your-server.com \
  --username your_user \
  --dbname your_db \
  --random \
  --limit "*=1000" \
  --file random_sample.sql \
  --verbose
```

### Use Case 8: Data-Only Export (Schema Already Exists)

**Scenario:** You already have the schema, just need data.

```bash
dbsample \
  --host your-server.com \
  --username your_user \
  --dbname your_db \
  --data-only \
  --limit "*=1000" \
  --file data_only.sql \
  --verbose
```

### Use Case 9: With SSL/TLS Connection

**Scenario:** Connecting to a remote database requiring SSL.

```bash
dbsample \
  --host secure-db.example.com \
  --username your_user \
  --dbname your_db \
  --ssl-mode require \
  --ssl-ca /path/to/ca-cert.pem \
  --limit "*=1000" \
  --file secure_sample.sql \
  --verbose
```

Or with client certificates:
```bash
dbsample \
  --host secure-db.example.com \
  --username your_user \
  --dbname your_db \
  --ssl-mode verify-full \
  --ssl-cert /path/to/client-cert.pem \
  --ssl-key /path/to/client-key.pem \
  --ssl-ca /path/to/ca-cert.pem \
  --limit "*=1000" \
  --file secure_sample.sql \
  --verbose
```

### Use Case 10: With Audit Trail

**Scenario:** You need to track what was sampled for compliance.

```bash
dbsample \
  --host your-server.com \
  --username your_user \
  --dbname your_db \
  --limit "*=1000" \
  --file sample.sql \
  --audit-file audit.json \
  --log-file sampling.log \
  --verbose
```

**What this creates:**
- `sample.sql` - The actual sample data
- `audit.json` - JSON file with sampling metadata
- `sampling.log` - Detailed log file

### Use Case 11: Compressed Output

**Scenario:** You want to compress the output file to save disk space.

```bash
# Method 1: Use --compress flag (auto-appends .gz if not present)
dbsample \
  --host your-server.com \
  --username your_user \
  --dbname your_db \
  --limit "*=1000" \
  --file sample.sql \
  --compress \
  --verbose

# Method 2: Use .gz extension (auto-enables compression)
dbsample \
  --host your-server.com \
  --username your_user \
  --dbname your_db \
  --limit "*=1000" \
  --file sample.sql.gz \
  --verbose
```

**What this does:**
- Compresses output using gzip
- Reduces file size significantly (often 70-90% reduction)
- File can be decompressed with `gunzip` or `gzip -d`
- Self-test (`--self-test`) automatically handles compressed files

### Use Case 12: Using Configuration Files

**Scenario:** You have complex sampling rules and want to store them in a file.

**Option 1: JSON Configuration (`config.json`):**
```json
{
  "host": "your-server.com",
  "username": "your_user",
  "dbname": "your_db",
  "limit": [
    "users=10000",
    "orders=5000",
    "*=100"
  ],
  "exclude_column": [
    "users.password",
    "*.api_key"
  ],
  "exclude_schema": ["audit", "logs"],
  "file": "sample.sql.gz",
  "compress": true,
  "verbose": true,
  "verify": true
}
```

**Option 2: YAML Configuration (`config.yaml`):**
```yaml
# Database connection
host: your-server.com
username: your_user
dbname: your_db
port: 5432
ssl_mode: prefer

# Output settings
file: sample.sql.gz
compress: true

# Sampling limits
limit:
  - "users=10000"
  - "orders=5000"
  - "*=100"

# Exclusions
exclude_column:
  - "users.password"
  - "*.api_key"

exclude_schema:
  - "audit"
  - "logs"

# Options
verbose: true
verify: true
log_level: INFO
```

**Run with config:**
```bash
# Using JSON
dbsample --config config.json

# Using YAML
dbsample --config config.yaml
```

**Or override config values with CLI:**
```bash
dbsample --config config.json --limit "*=200" --file override.sql
dbsample --config config.yaml --limit "*=200" --file override.sql
```

**What this does:**
- Loads settings from JSON or YAML file (both formats supported)
- YAML format is more readable for complex configurations
- CLI arguments override config file values
- Useful for complex, repeatable sampling scenarios
- Supports all CLI options

### Use Case 13: Dry-Run and Verification

**Scenario:** You want to preview what will be sampled before running.

```bash
# Step 1: Preview the sampling plan
dbsample \
  --host your-server.com \
  --username your_user \
  --dbname your_db \
  --limit "*=1000" \
  --dry-run \
  --verbose

# Step 2: Run actual sampling with verification
dbsample \
  --host your-server.com \
  --username your_user \
  --dbname your_db \
  --limit "*=1000" \
  --file sample.sql \
  --verify \
  --verbose

# Step 3: Run self-test to validate the output
dbsample \
  --host your-server.com \
  --username your_user \
  --dbname your_db \
  --limit "*=1000" \
  --file sample.sql \
  --self-test \
  --verbose
```

**What this does:**
- `--dry-run`: Shows table counts and sampling plan without executing
- `--verify`: Checks referential integrity after sampling
- `--self-test`: Creates temporary database, imports SQL, and validates

## Importing the Sample

After generating the sample SQL file, import it into your target database:

```bash
# Create target database
createdb -U postgres sample_db

# Import the sample (uncompressed)
psql -U postgres -d sample_db -f sample.sql

# Import compressed sample
gunzip -c sample.sql.gz | psql -U postgres -d sample_db
# Or: zcat sample.sql.gz | psql -U postgres -d sample_db

# Verify
psql -U postgres -d sample_db -c "SELECT COUNT(*) FROM users;"
```

Or on Windows:
```cmd
createdb -U postgres sample_db
psql -U postgres -d sample_db -f sample.sql
psql -U postgres -d sample_db -c "SELECT COUNT(*) FROM users;"
```

**Note:** For compressed files on Windows, you may need to decompress first using a tool like 7-Zip or use PowerShell:
```powershell
Get-Content sample.sql.gz | ForEach-Object { [System.Text.Encoding]::UTF8.GetString([System.IO.File]::ReadAllBytes($_)) } | psql -U postgres -d sample_db
```

## Real-World Examples

### Example 1: Production to Staging

```bash
# Sample from production
dbsample \
  --host prod-db.company.com \
  --username readonly_user \
  --dbname production \
  --limit "users=5000,orders=10000,products=1000,*=500" \
  --exclude-column "users.password,users.credit_card,*.api_key" \
  --exclude-schema audit \
  --file staging_sample.sql \
  --audit-file staging_audit.json \
  --verbose

# Import to staging
psql -U postgres -h staging-db.company.com -d staging -f staging_sample.sql
```

### Example 2: Large Database Sampling

```bash
# Use percentage-based sampling for very large tables
dbsample \
  --host large-db.company.com \
  --username analyst \
  --dbname analytics_db \
  --limit "events=1%,sessions=2%,users=5%,*=1000" \
  --file analytics_sample.sql \
  --verbose
```

### Example 3: Multi-Schema Database

```bash
# Sample from multiple schemas, exclude others
dbsample \
  --host db.company.com \
  --username dev_user \
  --dbname main_db \
  --schema app \
  --schema billing \
  --exclude-schema logs \
  --exclude-schema temp \
  --limit "*=1000" \
  --file app_sample.sql \
  --verbose
```

## Command-Line Options Reference

### Connection Options
- `--host, -h` - Database host (or `PGHOST` env var)
- `--port, -p` - Database port (default: 5432, or `PGPORT` env var)
- `--username, -U` - Username (or `PGUSER` env var)
- `--password, -W` - Password (or `PGPASSWORD` env var, or use .pgpass)
- `--dbname, -d` - Database name (or `PGDATABASE` env var)
- `--connection-uri` - Full PostgreSQL connection URI

### SSL Options
- `--ssl-mode` - SSL mode: disable, allow, prefer, require, verify-ca, verify-full (default: prefer)
- `--ssl-cert` - Client SSL certificate file
- `--ssl-key` - Client SSL key file
- `--ssl-ca` - SSL CA certificate file

### Sampling Options
- `--limit` - Row limits (can specify multiple times)
  - Format: `pattern=value` (e.g., `users=1000`, `users=10%`, `users=*`, `users=status='active'`)
- `--ordered` - Enable deterministic ordering
- `--ordered-desc` - Descending order (default when ordered)
- `--ordered-asc` - Ascending order
- `--random` - Random row selection

### Filtering Options
- `--schema` - Include specific schema (can specify multiple)
- `--exclude-schema` - Exclude entire database schema(s) and all their tables (can specify multiple)
- `--exclude-table` - Exclude specific table(s) using patterns (can specify multiple, supports wildcards)
- `--exclude-column` - Exclude specific column(s) using patterns (can specify multiple, supports wildcards)

### Output Options
- `--file, -f` - Output file path (default: stdout)
- `--compress, --gzip` - Compress output using gzip (auto-enabled if file ends with .gz)
- `--encoding, -E` - Character encoding (default: UTF-8)
- `--data-only, -a` - Export data without schema

### Logging Options
- `--verbose, -v` - Verbose output
- `--log-level` - Log level: ERROR, WARN, INFO, DEBUG (default: INFO)
- `--log-file` - Log file path
- `--audit-file` - Audit trail JSON file

### Configuration Options
- `--config, -c` - Configuration file path (JSON or YAML format)

### Other Options
- `--target-version` - Target PostgreSQL version for SQL output
- `--dry-run` - Show what would be sampled (displays table counts and sampling plan)
- `--verify` - Verify referential integrity after sampling
- `--self-test` - Run end-to-end test (creates temporary database, imports, and verifies)

## Exclusion Options Explained

The tool provides three types of exclusions that work at different levels:

### 1. `--exclude-schema` (Schema-Level Exclusion)

Excludes entire database schemas and all tables within them.

**Examples:**
```bash
# Exclude entire schemas
dbsample --exclude-schema audit --exclude-schema logs --limit "*=100"

# Exclude multiple schemas
dbsample --exclude-schema archive --exclude-schema temp --exclude-schema backup --limit "*=100"
```

**Use cases:**
- Excluding large audit/log schemas
- Skipping archive or backup schemas
- Removing entire functional areas from the sample

### 2. `--exclude-table` (Table-Level Exclusion)

Excludes specific tables. Supports wildcard patterns for flexible matching.

**Pattern Examples:**
- `users` - Excludes table named `users` in any schema
- `public.users` - Excludes `users` table in `public` schema
- `audit.*` - Excludes all tables in `audit` schema
- `*_log` - Excludes all tables ending with `_log`
- `temp_*` - Excludes all tables starting with `temp_`
- `*_backup_*` - Excludes all tables containing `_backup_`

**Examples:**
```bash
# Exclude specific tables
dbsample --exclude-table "users" --exclude-table "orders" --limit "*=100"

# Exclude tables with patterns
dbsample --exclude-table "audit.*" --exclude-table "*_log" --limit "*=100"

# Mix qualified and unqualified names
dbsample --exclude-table "public.users" --exclude-table "temp_*" --limit "*=100"
```

**Use cases:**
- Excluding specific large tables
- Skipping temporary or staging tables
- Removing log tables across multiple schemas

### 3. `--exclude-column` (Column-Level Exclusion)

Excludes specific columns from tables. Excluded columns are replaced with `NULL` in the output. Supports wildcard patterns.

**Pattern Examples:**
- `users.password` - Excludes `password` column in `users` table
- `*.password` - Excludes `password` column in all tables
- `users.*token*` - Excludes all columns containing `token` in `users` table
- `*.ssn` - Excludes `ssn` column in all tables
- `audit.*.ip_address` - Excludes `ip_address` column in all tables in `audit` schema

**Examples:**
```bash
# Exclude specific columns
dbsample --exclude-column "users.password" --exclude-column "users.email" --limit "*=100"

# Exclude columns with patterns
dbsample --exclude-column "*.password" --exclude-column "*.ssn" --limit "*=100"

# Exclude sensitive data patterns
dbsample --exclude-column "*.password" --exclude-column "*.secret_key" --exclude-column "users.*token*" --limit "*=100"
```

**Use cases:**
- Removing sensitive data (passwords, SSNs, API keys)
- Excluding large binary columns
- Masking PII for compliance

### Combining Exclusion Options

You can combine all three exclusion types in a single command:

```bash
dbsample \
  --host your-server.com \
  --username your_user \
  --dbname your_db \
  --exclude-schema archive \
  --exclude-schema logs \
  --exclude-table "temp_*" \
  --exclude-table "audit.*_backup" \
  --exclude-column "*.password" \
  --exclude-column "*.ssn" \
  --exclude-column "users.*token*" \
  --limit "*=1000" \
  --file sample.sql \
  --verbose
```

**This example:**
- Excludes entire `archive` and `logs` schemas
- Excludes all tables starting with `temp_`
- Excludes all tables in `audit` schema ending with `_backup`
- Excludes `password` and `ssn` columns from all tables
- Excludes all token-related columns from `users` table

### Exclusion Precedence

1. **Schema exclusion** is checked first - if a schema is excluded, all its tables are excluded
2. **Table exclusion** is checked next - individual tables can be excluded even if their schema is included
3. **Column exclusion** is applied last - columns are excluded from tables that pass schema and table filters

**Note:** Excluded columns are replaced with `NULL` values. If a column is part of a foreign key, this may cause referential integrity issues. The tool will warn about such cases.

## Tips and Best Practices

1. **Start Small:** Test with `--limit "*=10"` first to verify it works
2. **Use Verbose:** Always use `--verbose` to see progress
3. **Check Logs:** Review log files for warnings or issues
4. **Test Import:** Always test importing the sample before using in production
5. **Exclude Sensitive Data:** Use `--exclude-column` for passwords, API keys, SSNs, etc.
6. **Use .pgpass:** Store passwords securely in .pgpass file
7. **Audit Trail:** Use `--audit-file` to track what was sampled
8. **Schema Filtering:** Use `--exclude-schema` to skip large log/audit schemas
9. **Table Filtering:** Use `--exclude-table` with patterns to exclude groups of tables
10. **Foreign Keys:** The tool automatically includes required rows for FK constraints
11. **Large Databases:** Use percentage-based limits for very large tables
12. **Pattern Testing:** Use `--dry-run` to verify exclusion patterns match the expected tables/columns

## Troubleshooting

### Connection Issues

**Error: "could not connect to server"**
- Check host and port are correct
- Verify PostgreSQL is running and accessible
- Check firewall rules
- Test with `psql` first: `psql -h host -U user -d dbname`

**Error: "password authentication failed"**
- Verify username and password
- Check .pgpass file format
- Try `PGPASSWORD` environment variable
- Use `--connection-uri` with password

### Permission Issues

**Error: "permission denied for table"**
- Grant SELECT permission: `GRANT SELECT ON ALL TABLES IN SCHEMA public TO your_user;`
- Grant USAGE on schema: `GRANT USAGE ON SCHEMA public TO your_user;`

### Performance Issues

**Tool is slow:**
- Use smaller limits for initial testing
- Exclude large log/audit schemas
- Use percentage-based sampling for very large tables
- Consider sampling during off-peak hours

**Out of memory:**
- Reduce sample sizes
- Process one schema at a time
- Use `--data-only` if schema is already created

## Getting Help

View all options:
```bash
dbsample --help
```

Check version:
```bash
dbsample --version
```

Enable debug logging:
```bash
dbsample --log-level DEBUG --log-file debug.log ...
```

