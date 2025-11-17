# PostgreSQL Database Sampling Utility
## Requirements Document

**Version:** 1.0  
**Date:** November 13, 2025  
**Status:** Draft  
**Target:** Internal Tool - MVP (V1.0)

---

## 1. Executive Summary

This document specifies requirements for a command-line utility that exports a representative sample dataset from a PostgreSQL database while maintaining referential integrity and supporting complex schema relationships.

### 1.1 Purpose
Enable developers and testers to create scaled-down versions of production databases for development, testing, and debugging purposes.

### 1.2 Scope
The utility will sample data from all tables in a PostgreSQL database, preserving relationships and constraints while allowing flexible control over sample size and composition.

### 1.3 Release Strategy
This requirements document focuses on V1.0 (MVP) for internal use. Features are prioritized as:
- **V1.0 (Critical)**: Core functionality required for basic operation
- **V1.1 (High Priority)**: Production-readiness enhancements
- **V2.0+ (Future)**: Advanced features and optimizations

---

## 2. Functional Requirements

### 2.1 Core Functionality

#### 2.1.1 Database Sampling
- **REQ-001**: The utility SHALL extract a subset of data from a source PostgreSQL database
- **REQ-002**: The utility SHALL include all tables from the source database in the sample
- **REQ-003**: The utility SHALL maintain referential integrity across all foreign key relationships
- **REQ-004**: The utility SHALL support circular dependencies between tables
- **REQ-005**: The utility SHALL handle tables containing JSON and JSONB column types
- **REQ-006**: The utility SHALL produce output compatible with standard PostgreSQL import tools

#### 2.1.2 Schema Handling
- **REQ-007**: The utility SHALL support creating a temporary sample schema (default: `_pg_sample`)
- **REQ-008**: The utility SHALL optionally drop existing sample schema via `--force` flag
- **REQ-009**: The utility SHALL optionally preserve sample schema via `--keep` flag
- **REQ-010**: The utility SHALL support filtering by specific schema via `--schema` option
- **REQ-011**: The utility SHALL export both schema definitions and data by default
- **REQ-012**: The utility SHALL support data-only export via `--data-only` flag

#### 2.1.3 Database Objects
- **REQ-013**: The utility SHALL include table schemas (CREATE TABLE statements) in output
- **REQ-014**: The utility SHALL include custom types and domains referenced by tables
- **REQ-015**: The utility SHALL include views that reference sampled tables
- **REQ-016**: The utility SHALL include materialized views that reference sampled tables
- **REQ-017**: The utility SHALL include indexes defined on sampled tables
- **REQ-018**: The utility SHALL include triggers defined on sampled tables
- **REQ-019**: The utility SHALL include stored procedures and functions referenced by triggers or constraints
- **REQ-020**: The utility SHALL include PostgreSQL extensions required by sampled objects
- **REQ-021**: The utility SHALL maintain dependency order when creating database objects

#### 2.1.4 Constraints and Defaults
- **REQ-022**: The utility SHALL include all constraint types (PRIMARY KEY, FOREIGN KEY, UNIQUE, CHECK, NOT NULL)
- **REQ-023**: The utility SHALL include DEFAULT value expressions for columns
- **REQ-024**: The utility SHALL create PRIMARY KEY and UNIQUE constraints after data load for performance
- **REQ-025**: The utility SHALL create FOREIGN KEY constraints after all table data is loaded
- **REQ-026**: The utility SHALL preserve CHECK constraints in table definitions
- **REQ-027**: The utility SHALL handle multi-column constraints correctly

#### 2.1.5 Special Table Types
- **REQ-028**: The utility SHALL handle partitioned tables (both parent and child partitions)
- **REQ-029**: The utility SHALL sample data from appropriate partitions based on partition strategy
- **REQ-030**: The utility SHALL handle table inheritance hierarchies correctly
- **REQ-031**: The utility SHALL exclude temporary tables from sampling by default
- **REQ-032**: The utility SHALL provide clear error messages for unsupported table types (foreign tables, unlogged tables)

#### 2.1.6 Sequences and Identity Columns
- **REQ-033**: The utility SHALL include sequence definitions in output
- **REQ-034**: The utility SHALL include setval() calls to set sequence values appropriately
- **REQ-035**: The utility SHALL handle SERIAL pseudo-type columns correctly
- **REQ-036**: The utility SHALL handle IDENTITY columns (GENERATED ALWAYS/BY DEFAULT) correctly
- **REQ-037**: The utility SHALL determine appropriate sequence start values based on sampled data

### 2.2 Sampling Strategy

#### 2.2.1 Data Consistency
- **REQ-038**: The utility SHALL perform all sampling operations within a single database transaction
- **REQ-039**: The utility SHALL use REPEATABLE READ isolation level to ensure point-in-time consistency
- **REQ-040**: The utility SHALL handle concurrent database modifications by using snapshot isolation
- **REQ-041**: The utility SHALL document any limitations regarding long-running transactions

#### 2.2.2 Row Selection
- **REQ-042**: The utility SHALL default to sampling 100 rows per table
- **REQ-043**: The utility SHALL support global row limit via `--limit` option
- **REQ-044**: The utility SHALL support table-specific limits using pattern matching
- **REQ-045**: The utility SHALL support schema-wide limits using wildcard patterns (e.g., `schema.*`)
- **REQ-046**: The utility SHALL support percentage-based sampling (e.g., `10%`)
- **REQ-047**: The utility SHALL support conditional sampling using WHERE clause syntax
- **REQ-048**: The utility SHALL support full table inclusion using `*` notation
- **REQ-049**: The utility SHALL apply limit rules in order of specification with first match precedence
- **REQ-050**: The utility SHALL automatically include additional rows to satisfy foreign key constraints

#### 2.2.3 Row Ordering
- **REQ-051**: The utility SHALL support deterministic ordering via `--ordered` flag
- **REQ-052**: The utility SHALL order by primary key when deterministic ordering is enabled
- **REQ-053**: The utility SHALL handle tables without primary keys by using system columns (ctid)
- **REQ-054**: The utility SHALL support descending order via `--ordered-desc` (default)
- **REQ-055**: The utility SHALL support ascending order via `--ordered-asc`
- **REQ-056**: The utility SHALL support random row selection via `--random` flag

#### 2.2.4 Edge Cases
- **REQ-057**: The utility SHALL handle empty tables gracefully (include schema definition only)
- **REQ-058**: The utility SHALL handle empty databases gracefully
- **REQ-059**: The utility SHALL warn when limit patterns match zero tables
- **REQ-060**: The utility SHALL error gracefully when sampling tables with all columns excluded
- **REQ-061**: The utility SHALL provide clear messages when no data can be sampled

### 2.3 Exclusion and Filtering

#### 2.3.1 Table Exclusion
- **REQ-062**: The utility SHALL support excluding specific tables via `--exclude-table` option
- **REQ-063**: The utility SHALL support excluding tables using pattern matching (e.g., `log_*`)
- **REQ-064**: The utility SHALL support excluding multiple tables via repeated `--exclude-table` options
- **REQ-065**: The utility SHALL support comma-separated table lists in exclusion options

#### 2.3.2 Schema Exclusion
- **REQ-066**: The utility SHALL support excluding specific schemas via `--exclude-schema` option
- **REQ-067**: The utility SHALL support excluding multiple schemas via repeated `--exclude-schema` options
- **REQ-068**: The utility SHALL exclude system schemas by default (pg_catalog, information_schema)
- **REQ-069**: The utility SHALL provide option to include system schemas if explicitly requested

#### 2.3.3 Column Exclusion
- **REQ-070**: The utility SHALL support excluding specific columns via `--exclude-column` option
- **REQ-071**: The utility SHALL support column exclusion patterns (e.g., `users.password`, `*.secret_*`)
- **REQ-072**: The utility SHALL replace excluded column data with NULL values in output
- **REQ-073**: The utility SHALL maintain column definitions for excluded columns in schema output
- **REQ-074**: The utility SHALL support excluding multiple columns via repeated `--exclude-column` options

### 2.4 Output Control

#### 2.4.1 Output Destination
- **REQ-075**: The utility SHALL output to standard output by default
- **REQ-076**: The utility SHALL support file output via `--file` option
- **REQ-077**: The utility SHALL support character encoding specification via `--encoding` option
- **REQ-078**: The utility SHALL default to `PGCLIENTENCODING` environment variable if encoding not specified
- **REQ-079**: The utility SHALL default to database encoding if no encoding specified

#### 2.4.2 Output Format
- **REQ-080**: The utility SHALL generate valid SQL output
- **REQ-081**: The utility SHALL properly escape special characters in data
- **REQ-082**: The utility SHALL handle NULL values correctly
- **REQ-083**: The utility SHALL properly serialize JSON/JSONB data types
- **REQ-084**: The utility SHALL wrap all data operations in a single transaction (BEGIN/COMMIT)
- **REQ-085**: The utility SHALL include statement to disable triggers during data load (SESSION_REPLICATION_ROLE)
- **REQ-086**: The utility SHALL re-enable triggers after data load completes
- **REQ-087**: The utility SHALL handle output file write failures gracefully
- **REQ-088**: The utility SHALL check available disk space before writing (when writing to file)

### 2.5 Security and Authentication

#### 2.5.1 Credential Handling
- **REQ-089**: The utility SHALL support password input via environment variable (PGPASSWORD)
- **REQ-090**: The utility SHALL support password prompt when not provided via other means
- **REQ-091**: The utility SHALL support .pgpass file for password storage
- **REQ-092**: The utility SHALL support PostgreSQL connection URI format (postgresql://user:pass@host:port/db)
- **REQ-093**: The utility SHALL NOT display passwords in verbose output or logs
- **REQ-094**: The utility SHALL NOT include passwords in error messages

#### 2.5.2 Connection Security
- **REQ-095**: The utility SHALL support SSL/TLS connections via `--ssl-mode` option
- **REQ-096**: The utility SHALL support SSL modes: disable, allow, prefer, require, verify-ca, verify-full
- **REQ-097**: The utility SHALL default to 'prefer' SSL mode
- **REQ-098**: The utility SHALL support SSL certificate specification via `--ssl-cert`, `--ssl-key`, `--ssl-ca` options
- **REQ-099**: The utility SHALL validate SSL certificates when verify-ca or verify-full modes are used

#### 2.5.3 Output File Security
- **REQ-100**: The utility SHALL create output files with restrictive permissions (600 - owner read/write only)
- **REQ-101**: The utility SHALL warn if output file contains sensitive data and suggest secure handling

#### 2.5.4 Database Permissions
- **REQ-102**: The utility SHALL document minimum required database permissions (SELECT on tables, USAGE on schemas)
- **REQ-103**: The utility SHALL provide clear error messages when permissions are insufficient
- **REQ-104**: The utility SHALL skip tables where user lacks SELECT permission with a warning (when possible)

### 2.6 Validation and Testing

#### 2.6.1 Integrity Verification
- **REQ-105**: The utility SHALL provide an option to verify referential integrity after sampling via `--verify` flag
- **REQ-106**: The utility SHALL report any foreign key constraint violations found during verification
- **REQ-107**: The utility SHALL optionally validate that all sampled data can be successfully imported

#### 2.6.2 Dry-Run Mode
- **REQ-108**: The utility SHALL support dry-run mode via `--dry-run` flag
- **REQ-109**: In dry-run mode, the utility SHALL display which tables would be sampled
- **REQ-110**: In dry-run mode, the utility SHALL display estimated row counts per table
- **REQ-111**: In dry-run mode, the utility SHALL show which database objects would be included
- **REQ-112**: In dry-run mode, the utility SHALL NOT connect to or read from the database
- **REQ-113**: In dry-run mode, the utility SHALL NOT produce any output file

#### 2.6.3 Self-Test Mode
- **REQ-114**: The utility SHALL provide a self-test mode via `--self-test` flag
- **REQ-115**: Self-test mode SHALL create a temporary sample and attempt to restore it
- **REQ-116**: Self-test mode SHALL verify all foreign key constraints in the restored sample
- **REQ-117**: Self-test mode SHALL report success or failure with detailed diagnostics
- **REQ-118**: Self-test mode SHALL clean up temporary databases after completion

### 2.7 Logging and Auditing

#### 2.7.1 Logging Capabilities
- **REQ-119**: The utility SHALL log all major operations (connection, table processing, object creation)
- **REQ-120**: The utility SHALL log warnings for potential issues (missing indexes, large tables, etc.)
- **REQ-121**: The utility SHALL log timing information for performance analysis
- **REQ-122**: The utility SHALL support configurable log levels (ERROR, WARN, INFO, DEBUG) via `--log-level` option
- **REQ-123**: The utility SHALL output logs to stderr by default
- **REQ-124**: The utility SHALL support logging to a file via `--log-file` option

#### 2.7.2 Audit Trail
- **REQ-125**: The utility SHALL record which tables were sampled and row counts
- **REQ-126**: The utility SHALL record which columns were excluded
- **REQ-127**: The utility SHALL record all applied limit rules and their matches
- **REQ-128**: The utility SHALL record timestamp of sampling operation
- **REQ-129**: The utility SHALL record database connection details (host, port, database name)
- **REQ-130**: The utility SHALL optionally write audit trail to a separate file via `--audit-file` option
- **REQ-131**: Audit trail output SHALL be in machine-readable format (JSON recommended)

#### 2.7.3 Progress Reporting
- **REQ-132**: The utility SHALL display progress information when `--verbose` is enabled
- **REQ-133**: Progress information SHALL include current table being processed
- **REQ-134**: Progress information SHALL include tables completed vs total tables
- **REQ-135**: Progress information SHALL include estimated time remaining (when feasible)
- **REQ-136**: Progress information SHALL include current operation (schema dump, data sampling, etc.)
- **REQ-137**: The utility SHALL provide a summary report at completion (tables processed, rows sampled, duration)

---

## 3. Non-Functional Requirements

### 3.1 Performance
- **REQ-138**: The utility SHALL process databases with circular dependencies without infinite loops
- **REQ-139**: The utility SHOULD complete sampling of typical databases (< 1GB) within 5 minutes
- **REQ-140**: The utility SHALL provide progress feedback when `--verbose` is enabled
- **REQ-141**: Random sampling MAY significantly increase execution time (acceptable trade-off)
- **REQ-142**: The utility SHALL document memory requirements and limitations
- **REQ-143**: The utility SHALL handle large result sets without loading entire tables into memory (streaming approach)

### 3.2 Reliability
- **REQ-144**: The utility SHALL validate foreign key constraints before completion
- **REQ-145**: The utility SHALL handle connection failures gracefully
- **REQ-146**: The utility SHALL provide meaningful error messages
- **REQ-147**: The utility SHALL not modify the source database
- **REQ-148**: The utility SHALL properly clean up resources (connections, temp files) on exit or error
- **REQ-149**: The utility SHALL handle database transaction timeout appropriately

### 3.3 Compatibility and Portability

#### 3.3.1 PostgreSQL Version Compatibility
- **REQ-150**: The utility SHALL support PostgreSQL versions 9.6 through current stable release
- **REQ-151**: The utility SHALL detect source database PostgreSQL version
- **REQ-152**: The utility SHALL generate SQL output compatible with the source database version
- **REQ-153**: The utility SHALL optionally generate SQL for a different target PostgreSQL version via `--target-version` option
- **REQ-154**: The utility SHALL warn about version-specific features that may not be portable

#### 3.3.2 SQL Dialect Compatibility
- **REQ-155**: The utility SHALL generate standard PostgreSQL-compliant SQL by default
- **REQ-156**: The utility SHALL properly quote identifiers to handle reserved words and special characters
- **REQ-157**: The utility SHALL use explicit type casting where necessary for portability
- **REQ-158**: The utility SHALL avoid version-specific syntax when `--target-version` is specified

### 3.4 Usability
- **REQ-159**: The utility SHALL provide comprehensive help via `--help` option
- **REQ-160**: The utility SHALL support standard PostgreSQL connection parameters
- **REQ-161**: The utility SHALL output verbose status information via `--verbose` flag
- **REQ-162**: The utility SHALL support database client tracing/debugging via `--trace` option
- **REQ-163**: The utility SHALL provide examples in help output for common use cases

---

## 4. Interface Requirements

### 4.1 Command-Line Interface

#### 4.1.1 Database Connection Options
| Option | Short | Environment Variable | Description | Required |
|--------|-------|---------------------|-------------|----------|
| `--host` | `-h` | `PGHOST` | Database host address | No |
| `--port` | `-p` | `PGPORT` | Database port number | No |
| `--username` | `-U` | `PGUSER` | Connection username | No |
| `--password` | `-W` | `PGPASSWORD` | Connection password (prompts if needed) | No |
| `--connection-uri` | - | - | PostgreSQL connection URI | No |
| `dbname` | - | `PGDATABASE` | Database name | No* |

*If dbname not specified, defaults to `PGDATABASE` environment variable or current username

#### 4.1.2 Security Options
| Option | Default | Description |
|--------|---------|-------------|
| `--ssl-mode` | prefer | SSL mode (disable, allow, prefer, require, verify-ca, verify-full) |
| `--ssl-cert` | - | Client SSL certificate file path |
| `--ssl-key` | - | Client SSL key file path |
| `--ssl-ca` | - | SSL CA certificate file path |

#### 4.1.2 Security Options
| Option | Default | Description |
|--------|---------|-------------|
| `--ssl-mode` | prefer | SSL mode (disable, allow, prefer, require, verify-ca, verify-full) |
| `--ssl-cert` | - | Client SSL certificate file path |
| `--ssl-key` | - | Client SSL key file path |
| `--ssl-ca` | - | SSL CA certificate file path |

#### 4.1.3 Sampling Control Options
| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--limit` | - | `100` | Row limit (global or pattern-based) |
| `--ordered` | - | off | Enable deterministic ordering |
| `--ordered-desc` | - | on (when ordered) | Descending order |
| `--ordered-asc` | - | off | Ascending order |
| `--random` | - | off | Randomize row selection |

#### 4.1.4 Output Control Options
| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--file` | `-f` | stdout | Output file path |
| `--encoding` | `-E` | `PGCLIENTENCODING` or DB encoding | Character encoding |
| `--data-only` | `-a` | off | Export data without schema |

#### 4.1.5 Schema Management Options
| Option | Default | Description |
|--------|---------|-------------|
| `--schema` | all | Specific schema to export |
| `--sample-schema` | `_pg_sample` | Temporary schema name |
| `--force` | off | Drop existing sample schema |
| `--keep` | off | Preserve sample schema |

#### 4.1.6 Exclusion Options
| Option | Default | Description |
|--------|---------|-------------|
| `--exclude-table` | none | Exclude specific table(s) - supports patterns |
| `--exclude-schema` | system schemas | Exclude specific schema(s) |
| `--exclude-column` | none | Exclude specific column(s) - supports patterns |

#### 4.1.7 Validation and Testing Options
| Option | Default | Description |
|--------|---------|-------------|
| `--verify` | off | Verify referential integrity after sampling |
| `--dry-run` | off | Show what would be sampled without executing |
| `--self-test` | off | Run end-to-end test of sample and restore |

#### 4.1.8 Logging and Audit Options
| Option | Default | Description |
|--------|---------|-------------|
| `--log-level` | INFO | Set logging level (ERROR, WARN, INFO, DEBUG) |
| `--log-file` | stderr | Write logs to specified file |
| `--audit-file` | none | Write audit trail to specified file (JSON format) |

#### 4.1.9 Compatibility Options
| Option | Default | Description |
|--------|---------|-------------|
| `--target-version` | source version | Target PostgreSQL version for generated SQL |

#### 4.1.10 Diagnostic Options
| Option | Description |
|--------|-------------|
| `--help` | Display usage information |
| `--verbose` | Output status messages to stderr |
| `--trace` | Enable database client tracing/debugging |

### 4.2 Exit Codes

The utility SHALL use the following exit codes for automation and scripting:

| Exit Code | Meaning |
|-----------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Database connection failure |
| 3 | Permission denied / insufficient privileges |
| 4 | Referential integrity violation |
| 5 | Configuration/option error |
| 6 | Disk space or I/O error |
| 7 | Transaction timeout |

### 4.3 Limit Pattern Syntax

The `--limit` option supports multiple formats:

```
# Format: <pattern> = <rule>

# Numeric limits
users = 1000              # Exactly 1000 rows
* = 500                   # Default 500 rows for all tables

# Percentage-based
users = 10%               # 10% of total rows

# Full table
users = *                 # All rows

# Conditional (WHERE clause)
users = NOT deactivated   # All active users

# Schema wildcards
schema.* = 100            # All tables in schema
log.* = 5%                # 5% from all log tables

# Multiple rules (comma-separated)
--limit="ads=*,users=1000,*=300"

# Multiple --limit options (processed in order)
--limit="users=*" --limit="*=100"
```

### 4.3 Exclusion Pattern Syntax

The exclusion options support pattern matching:

```
# Exclude specific tables
--exclude-table=audit_log
--exclude-table=temp_*           # All tables starting with temp_

# Exclude specific schemas
--exclude-schema=archive
--exclude-schema=logs

# Exclude specific columns
--exclude-column=users.password
--exclude-column=*.ssn           # Column 'ssn' in all tables
--exclude-column=users.*token*   # All token-related columns in users

# Multiple exclusions
--exclude-table=logs --exclude-table=temp_data --exclude-schema=archive
```

---

## 5. Data Integrity Requirements

### 5.1 Referential Integrity
- **REQ-164**: The utility SHALL include all rows required to satisfy foreign key constraints
- **REQ-165**: The utility SHALL handle multi-column foreign keys
- **REQ-166**: The utility SHALL handle self-referencing foreign keys
- **REQ-167**: The utility SHALL resolve circular dependencies correctly
- **REQ-168**: The utility SHALL maintain constraint order during data insertion

### 5.2 Data Type Support
- **REQ-169**: The utility SHALL support all standard PostgreSQL data types
- **REQ-170**: The utility SHALL correctly serialize JSON data types
- **REQ-171**: The utility SHALL correctly serialize JSONB data types
- **REQ-172**: The utility SHALL handle array types
- **REQ-173**: The utility SHALL handle custom/composite types
- **REQ-174**: The utility SHALL handle large objects (BLOBs) appropriately

### 5.3 Database Object Dependencies
- **REQ-175**: The utility SHALL resolve and include all type dependencies before table creation
- **REQ-176**: The utility SHALL create extensions before objects that depend on them
- **REQ-177**: The utility SHALL handle view dependencies on tables correctly
- **REQ-178**: The utility SHALL create base tables before materialized views that reference them
- **REQ-179**: The utility SHALL preserve function/procedure dependencies for triggers
- **REQ-180**: The utility SHALL output database objects in correct dependency order

---

## 6. Error Handling Requirements

- **REQ-181**: The utility SHALL exit with appropriate status codes as defined in section 4.2
- **REQ-182**: The utility SHALL output error messages to stderr
- **REQ-183**: The utility SHALL provide context in error messages (table name, constraint, etc.)
- **REQ-184**: The utility SHALL handle connection timeout gracefully
- **REQ-185**: The utility SHALL handle insufficient permissions gracefully
- **REQ-186**: The utility SHALL validate pattern syntax before execution
- **REQ-187**: The utility SHALL warn when excluded columns break foreign key constraints
- **REQ-188**: The utility SHALL error when attempting to exclude tables required by foreign keys (unless forced)
- **REQ-189**: The utility SHALL provide suggestions for fixing common errors in error messages
- **REQ-190**: The utility SHALL log detailed error information at DEBUG level for troubleshooting

---

## 7. Constraints and Assumptions

### 7.1 Technical Constraints
- PostgreSQL version 9.6 or higher required
- Sufficient permissions to read all tables in target database (SELECT, USAGE on schemas)
- Sufficient disk space for output file (if specified)
- Network connectivity to database server
- For large databases (>10GB), adequate memory for transaction management

### 7.2 Assumptions
- Source database is accessible and operational
- User has SELECT privileges on all tables to be sampled
- Foreign key constraints are properly defined in the database
- Primary keys exist for deterministic ordering (when requested)
- Database is not undergoing major schema changes during sampling
- Output will be imported into PostgreSQL (not other database systems)

---

## 8. Future Considerations

### 8.1 Potential Enhancements (V1.1 - High Priority)
- **Configuration file support** - YAML/JSON config for complex sampling rules
- **Foreign table handling** - Support for Foreign Data Wrapper tables
- **Unlogged table support** - Handle unlogged tables appropriately
- **Advanced memory management** - Sophisticated handling of very large tables
- **Streaming compression** - Gzip output on-the-fly
- **Resume capability** - Checkpoint and resume interrupted operations

### 8.2 Future Features (V2.0+)
- **Parallel processing** - Improve performance via parallel table sampling
- **Incremental sampling** - Delta exports for updated data
- **GUI interface** - Visual configuration of sampling rules
- **Alternative export formats** - CSV, JSON, Parquet
- **Temporal sampling** - Sample based on data age or time ranges
- **Data anonymization** - Built-in PII masking/pseudonymization
- **Cloud storage integration** - Direct export to S3, Azure Blob, GCS
- **Database migration tool integration** - Flyway, Liquibase compatibility
- **Cross-database support** - MySQL, Oracle, SQL Server

### 8.3 Known Limitations (V1.0)
- Random sampling may significantly impact performance
- Very large tables (>100M rows) may require substantial memory
- Complex circular dependencies may require multiple passes
- Dry-run mode provides estimates only; actual row counts may vary due to constraint resolution
- Foreign tables (FDW) are not supported and will be skipped with warning
- Unlogged tables are not supported and will be skipped with warning
- Row Level Security (RLS) policies are not evaluated; all visible rows are sampled
- No built-in data anonymization; sensitive data should be excluded via `--exclude-column`

---

## 9. Acceptance Criteria

### 9.1 V1.0 (MVP) Acceptance Criteria

The utility will be considered complete for V1.0 when:

#### Core Functionality
1. All critical functional requirements (REQ-001 through REQ-137) are implemented
2. All non-functional requirements (REQ-138 through REQ-163) are met
3. All data integrity requirements (REQ-164 through REQ-180) are satisfied
4. All error handling requirements (REQ-181 through REQ-190) are implemented

#### Data Integrity
5. Sample output can be successfully imported into a fresh PostgreSQL database
6. Referential integrity is maintained in all test scenarios
7. Circular dependencies are handled correctly in test cases
8. JSON/JSONB columns are properly exported and importable
9. All constraint types (PK, FK, UNIQUE, CHECK, NOT NULL, DEFAULT) are preserved
10. Sequences and IDENTITY columns work correctly after import

#### Database Object Support
11. Database objects (views, indexes, triggers, functions, extensions) are correctly exported
12. Custom types and domains are properly included
13. Partitioned tables and inherited tables are handled correctly
14. Empty tables and databases are handled gracefully

#### Filtering and Exclusion
15. Exclusion filters work correctly for tables, schemas, and columns
16. Excluded columns do not break foreign key relationships (or appropriate warnings are given)
17. Limit patterns correctly match tables and apply rules in precedence order

#### Security and Authentication
18. All authentication methods work correctly (.pgpass, environment, prompt, URI)
19. SSL/TLS connections function as specified
20. Output files have appropriate restrictive permissions
21. Passwords are never displayed in logs or error messages

#### Validation and Testing
22. Dry-run mode accurately predicts sampling behavior without database access
23. Self-test mode successfully validates end-to-end functionality
24. Verify mode correctly identifies referential integrity issues

#### Logging and Progress
25. Logging and audit trails contain complete and accurate information
26. Progress reporting provides meaningful feedback to users
27. Summary statistics are accurate and informative

#### Compatibility
28. Generated SQL is compatible with specified target PostgreSQL versions
29. Tool works on PostgreSQL 9.6 through current stable release
30. Exit codes correctly reflect different failure scenarios

#### Documentation
31. Comprehensive help output is available via `--help`
32. Common use cases are documented with examples
33. Error messages are clear and actionable
34. Known limitations are documented

### 9.2 V1.1 Acceptance Criteria (Production Ready)

In addition to V1.0 criteria:
35. Configuration file support is implemented and functional
36. Foreign tables are handled appropriately (with warnings or support)
37. Advanced memory management handles very large tables efficiently
38. Performance meets targets (<5 min for <1GB databases)

---

## 10. Glossary

| Term | Definition |
|------|------------|
| **Referential Integrity** | Database constraint ensuring relationships between tables remain consistent |
| **Circular Dependency** | Two or more tables with foreign keys referencing each other |
| **Deterministic Ordering** | Consistent row ordering based on primary key |
| **Sample Schema** | Temporary database schema used for staging sampled data |
| **Pattern Matching** | Wildcard-based table name matching for applying rules |

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-13 | - | Initial draft |

---

## Approval

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Product Owner | | | |
| Technical Lead | | | |
| QA Lead | | | |