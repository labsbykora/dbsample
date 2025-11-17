# Database Sampling Utility

A command-line utility that exports a representative sample dataset from databases (currently PostgreSQL) while maintaining referential integrity and supporting complex schema relationships.

## Features

- **Referential Integrity**: Automatically includes all rows required to satisfy foreign key constraints
- **Flexible Sampling**: Support for numeric limits, percentages, conditional sampling, and full table inclusion
- **Pattern Matching**: Apply rules to specific tables, schemas, or use wildcards
- **Schema Export**: Includes tables, views, indexes, triggers, functions, types, and sequences
- **Security**: SSL/TLS support, secure credential handling, restrictive file permissions
- **Staging Mode**: Optional staging schema for large databases with automatic cleanup
- **Dry-Run Mode**: Preview what would be sampled without executing
- **Progress Bars**: Visual progress indicators for long-running operations
- **Verification**: Referential integrity verification (`--verify` flag)
- **Self-Test**: End-to-end validation with temporary database (`--self-test` flag)
- **Gzip Compression**: Compress output files with `--compress` or `.gz` extension
- **Configuration Files**: Load settings from JSON or YAML files (`--config` flag)

## Installation

```bash
pip install -e .
```

**Note**: If upgrading from v1.x (`pg-sample`), see [MIGRATION_GUIDE_v2.0.0.md](MIGRATION_GUIDE_v2.0.0.md) for breaking changes.

## Usage

```bash
# Basic usage - sample 100 rows per table
dbsample --host localhost --username myuser --dbname mydb

# Custom limits with patterns
dbsample --host localhost --username myuser --dbname mydb \
  --limit "users=1000,orders=500,*=100"

# Exclude sensitive columns
dbsample --host localhost --username myuser --dbname mydb \
  --exclude-column "users.password,*.ssn"

# Exclude entire schemas
dbsample --host localhost --username myuser --dbname mydb \
  --exclude-schema audit --exclude-schema logs

# Exclude specific tables (supports patterns)
dbsample --host localhost --username myuser --dbname mydb \
  --exclude-table "temp_*" --exclude-table "audit.*"

# Output to file
dbsample --host localhost --username myuser --dbname mydb \
  --file sample.sql

# Dry run to see what would be sampled
dbsample --host localhost --username myuser --dbname mydb --dry-run

# Use configuration file
dbsample --config config.json

# Compress output
dbsample --host localhost --username myuser --dbname mydb --file output.sql.gz --compress
```

## Requirements

- Python 3.8+
- PostgreSQL 9.6+
- SELECT privileges on tables to be sampled

## Documentation

See `pg_sample_requirements.md` for complete requirements and specifications (note: filename retained for historical reference).

