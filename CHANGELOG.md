# Changelog

All notable changes to the PostgreSQL Database Sampling Utility will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-11-17

### Added
- **IDENTITY Column Support**: Full support for PostgreSQL 10+ IDENTITY columns (GENERATED ALWAYS/BY DEFAULT)
  - Automatically detects IDENTITY columns
  - Includes IDENTITY sequences in setval() calls
  - Gracefully handles older PostgreSQL versions
- **Version in Export Headers**: Export files now include tool version in header
- **Enhanced Verbose Logging**: Much more detailed progress information with `--verbose`
  - Per-table sampling progress
  - Foreign key resolution details
  - Sequence processing information
  - Output generation progress
  - Timing information
- **FK Warnings**: Warns when foreign keys reference tables without primary keys
- **Excluded Sequence Column Handling**: Queries source database for max values when sequence columns are excluded
- **Limit Pattern Validation**: Warns when limit patterns match zero tables
- **Comprehensive Export Headers**: Export files include detailed metadata:
  - Source database information
  - Export statistics
  - Sampling options
  - Exclusion information
  - Database object counts

### Changed
- **Sequence Multi-Column Support**: Sequences used by multiple columns now calculate max across all columns
- **Percentage Display**: Whole number percentages now display as "1%" instead of "1.0%"
- **Transaction Management**: Improved transaction handling with autocommit mode
- **Error Handling**: Better error messages and fail-fast strategy
- **Documentation**: Updated all documentation to reflect current implementation

### Fixed
- **Invalid CREATE TYPE Statements**: Fixed generation of invalid type definitions
- **Transaction Abort Cascades**: Fixed "InFailedSqlTransaction" errors with proper rollback handling
- **Staging Table Quoting**: Fixed incorrect table name quoting in staging mode
- **Sequence Setval**: Properly generates setval() calls for all sequence types
- **Type Definitions**: Correctly handles composite, domain, and enum types
- **Table Type Filtering**: Filters out table types from custom type definitions

### Removed
- **Unimplemented Flags**: Removed `--verify` and `--self-test` flags (to be implemented in future release)
- **Unused Code**: Removed unused variables and imports

### Improved
- **Code Quality**: Added constants for magic numbers
- **Logging**: Enhanced verbose logging throughout the application
- **Error Messages**: More descriptive error messages with context
- **Documentation**: Comprehensive documentation updates

---

## [Unreleased]

### Planned
- Streaming for very large tables (deferred to future version)

## [1.2.0] - 2025-11-17

### Added
- **Gzip Compression**: Support for compressing output files
  - `--compress` / `--gzip` flag to enable compression
  - Auto-detection: files ending with `.gz` are automatically compressed
  - Compressed files show "(compressed)" in verbose output
  - Compatible with standard `gunzip` and `zcat` tools
- **Configuration File Support**: Load settings from JSON or YAML files
  - `--config` / `-c` flag to specify configuration file
  - Supports JSON format (built-in)
  - Supports YAML format (PyYAML included in requirements)
  - CLI arguments take precedence over config file values
  - Key normalization (e.g., `database` → `dbname`, `output` → `file`)
  - All CLI options can be specified in config file

### Changed
- **File Permissions**: File permissions are now set after file is closed (fixes issue with compressed files)

## [1.1.0] - 2025-11-17

### Added
- **Dry-Run Mode**: Full implementation of `--dry-run` flag
  - Connects to database and discovers schema
  - Fetches table row counts (using `pg_stat_user_tables` with fallback)
  - Calculates estimated rows to be sampled based on limit rules
  - Displays comprehensive sampling plan with table-by-table breakdown
  - Shows total summary and configuration details
  - Exits without sampling or generating output
- **Progress Bars**: ASCII progress bars throughout the sampling process
  - Shows progress for table sampling (direct and staging modes)
  - Displays progress for reading from staging tables
  - Shows progress for writing SQL output
  - Works in both verbose and non-verbose modes
  - Provides visual feedback with percentage completion
- **Verify Flag**: Referential integrity verification (`--verify` flag)
  - Verifies all foreign key constraints after sampling
  - Checks that FK values in sampled data exist in referenced tables
  - Reports detailed violations with constraint names and sample values
  - Exits with error code if violations found
  - Works with both staging and direct sampling modes
- **Self-Test Flag**: End-to-end validation (`--self-test` flag)
  - Creates temporary database for testing
  - Runs full sampling process
  - Generates SQL output file
  - Imports SQL into temporary database
  - Verifies import succeeded
  - Validates all constraints are valid
  - Reports comprehensive test results
  - Automatically cleans up temporary resources
  - Creates temporary SQL file if output is to stdout

### Changed
- **Dry-Run Help Text**: Updated to reflect full implementation
- **Error Handling**: Improved error messages for verification failures

