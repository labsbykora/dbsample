"""Command-line interface for dbsample utility."""

import sys
import os
import stat
import time
import gzip
from typing import Optional, List
from datetime import datetime
import click
import psycopg
from dbsample.connection import DatabaseConnection
from dbsample.logger import Logger, LogLevel
from dbsample.schema import SchemaDiscovery
from dbsample.dependencies import DependencyResolver
from dbsample.sampling import SamplingEngine, parse_limit_rules
from dbsample.output import SQLOutputGenerator
from dbsample.staging import StagingManager
from dbsample.self_test import SelfTestRunner
from dbsample.config import load_config_file, merge_config_with_cli, normalize_config_keys


# Exit codes
EXIT_SUCCESS = 0
EXIT_GENERAL_ERROR = 1
EXIT_CONNECTION_ERROR = 2
EXIT_PERMISSION_ERROR = 3
EXIT_INTEGRITY_ERROR = 4
EXIT_CONFIG_ERROR = 5
EXIT_IO_ERROR = 6
EXIT_TIMEOUT_ERROR = 7


def parse_log_level(level_str: str) -> LogLevel:
    """Parse log level string."""
    level_map = {
        "ERROR": LogLevel.ERROR,
        "WARN": LogLevel.WARN,
        "INFO": LogLevel.INFO,
        "DEBUG": LogLevel.DEBUG,
    }
    return level_map.get(level_str.upper(), LogLevel.INFO)


@click.command()
@click.option("--config", "-c", type=click.Path(exists=True), help="Configuration file path (JSON or YAML)")
@click.option("--host", envvar="PGHOST", help="Database host address")
@click.option("--port", "-p", type=int, envvar="PGPORT", default=5432, help="Database port number")
@click.option("--username", "-U", envvar="PGUSER", help="Connection username")
@click.option("--password", "-W", envvar="PGPASSWORD", help="Connection password")
@click.option("--connection-uri", help="PostgreSQL connection URI")
@click.option("--dbname", "-d", envvar="PGDATABASE", help="Database name")
@click.option("--ssl-mode", default="prefer", help="SSL mode (disable, allow, prefer, require, verify-ca, verify-full)")
@click.option("--ssl-cert", help="Client SSL certificate file path")
@click.option("--ssl-key", help="Client SSL key file path")
@click.option("--ssl-ca", help="SSL CA certificate file path")
@click.option("--limit", multiple=True, help="Row limit (global or pattern-based)")
@click.option("--ordered", is_flag=True, help="Enable deterministic ordering")
@click.option("--ordered-desc", is_flag=True, default=True, help="Descending order (default)")
@click.option("--ordered-asc", is_flag=True, help="Ascending order")
@click.option("--random", is_flag=True, help="Randomize row selection")
@click.option("--file", "-f", type=click.Path(), help="Output file path (use .gz extension or --compress for gzip compression)")
@click.option("--compress", "--gzip", is_flag=True, help="Compress output using gzip (also auto-enabled if file ends with .gz)")
@click.option("--encoding", "-E", envvar="PGCLIENTENCODING", help="Character encoding")
@click.option("--data-only", "-a", is_flag=True, help="Export data without schema")
@click.option("--schema", multiple=True, help="Specific schema to export")
@click.option("--sample-schema", default="_dbsample", help="Temporary schema name for staging")
@click.option("--use-staging", is_flag=True, help="Explicitly enable staging mode (auto-enabled for large databases)")
@click.option("--no-staging", is_flag=True, help="Explicitly disable staging mode")
@click.option("--force", is_flag=True, help="Drop existing sample schema if it exists")
@click.option("--keep", is_flag=True, help="Preserve sample schema after completion (for debugging)")
@click.option("--exclude-table", multiple=True, help="Exclude specific table(s) - supports patterns")
@click.option("--exclude-schema", multiple=True, help="Exclude specific schema(s)")
@click.option("--exclude-column", multiple=True, help="Exclude specific column(s) - supports patterns")
@click.option("--dry-run", is_flag=True, help="Show what would be sampled without executing (displays table counts and sampling plan)")
@click.option("--verify", is_flag=True, help="Verify referential integrity after sampling (checks foreign key constraints)")
@click.option("--self-test", is_flag=True, help="Run end-to-end test: sample → generate SQL → import → verify (creates temporary database)")
@click.option("--log-level", default="INFO", type=click.Choice(["ERROR", "WARN", "INFO", "DEBUG"]), help="Set logging level")
@click.option("--log-file", type=click.Path(), help="Write logs to specified file")
@click.option("--audit-file", type=click.Path(), help="Write audit trail to specified file (JSON format)")
@click.option("--target-version", help="Target PostgreSQL version for generated SQL")
@click.option("--verbose", "-v", is_flag=True, help="Output status messages to stderr")
@click.option("--trace", is_flag=True, help="Enable database client tracing/debugging")
@click.version_option(version=None, package_name="dbsample", help="Show version and exit")
def main(
    config: Optional[str],
    host: Optional[str],
    port: int,
    username: Optional[str],
    password: Optional[str],
    connection_uri: Optional[str],
    dbname: Optional[str],
    ssl_mode: str,
    ssl_cert: Optional[str],
    ssl_key: Optional[str],
    ssl_ca: Optional[str],
    limit: tuple,
    ordered: bool,
    ordered_desc: bool,
    ordered_asc: bool,
    random: bool,
    file: Optional[str],
    compress: bool,
    encoding: Optional[str],
    data_only: bool,
    schema: tuple,
    sample_schema: str,
    use_staging: bool,
    no_staging: bool,
    force: bool,
    keep: bool,
    exclude_table: tuple,
    exclude_schema: tuple,
    exclude_column: tuple,
    dry_run: bool,
    verify: bool,
    self_test: bool,
    log_level: str,
    log_file: Optional[str],
    audit_file: Optional[str],
    target_version: Optional[str],
    verbose: bool,
    trace: bool,
):
    """Database Sampling Utility - Export representative sample datasets."""
    
    # Load configuration file if specified (before setting up logger)
    config_values = {}
    if config:
        try:
            config_values = load_config_file(config)
            config_values = normalize_config_keys(config_values)
        except Exception as e:
            # Create temporary logger for error message
            logger_temp = Logger()
            logger_temp.configure(level=LogLevel.ERROR)
            logger_temp.error(f"Failed to load configuration file: {e}")
            sys.exit(EXIT_CONFIG_ERROR)
    
    # Merge config with CLI arguments (CLI takes precedence)
    if config_values:
        # Convert CLI args to dict for merging
        cli_args_dict = {
            'host': host,
            'port': port,
            'username': username,
            'password': password,
            'connection_uri': connection_uri,
            'dbname': dbname,
            'ssl_mode': ssl_mode,
            'ssl_cert': ssl_cert,
            'ssl_key': ssl_key,
            'ssl_ca': ssl_ca,
            'limit': limit,
            'ordered': ordered,
            'ordered_desc': ordered_desc,
            'ordered_asc': ordered_asc,
            'random': random,
            'file': file,
            'compress': compress,
            'encoding': encoding,
            'data_only': data_only,
            'schema': schema,
            'sample_schema': sample_schema,
            'use_staging': use_staging,
            'no_staging': no_staging,
            'force': force,
            'keep': keep,
            'exclude_table': exclude_table,
            'exclude_schema': exclude_schema,
            'exclude_column': exclude_column,
            'dry_run': dry_run,
            'verify': verify,
            'self_test': self_test,
            'log_level': log_level,
            'log_file': log_file,
            'audit_file': audit_file,
            'target_version': target_version,
            'verbose': verbose,
            'trace': trace,
        }
        
        merged_config = merge_config_with_cli(config_values, cli_args_dict)
        
        # Update variables from merged config
        host = merged_config.get('host', host)
        port = merged_config.get('port', port)
        username = merged_config.get('username', username)
        password = merged_config.get('password', password)
        connection_uri = merged_config.get('connection_uri', connection_uri)
        dbname = merged_config.get('dbname', dbname)
        ssl_mode = merged_config.get('ssl_mode', ssl_mode)
        ssl_cert = merged_config.get('ssl_cert', ssl_cert)
        ssl_key = merged_config.get('ssl_key', ssl_key)
        ssl_ca = merged_config.get('ssl_ca', ssl_ca)
        limit = tuple(merged_config.get('limit', limit)) if merged_config.get('limit') else limit
        ordered = merged_config.get('ordered', ordered)
        ordered_desc = merged_config.get('ordered_desc', ordered_desc)
        ordered_asc = merged_config.get('ordered_asc', ordered_asc)
        random = merged_config.get('random', random)
        file = merged_config.get('file', file)
        compress = merged_config.get('compress', compress)
        encoding = merged_config.get('encoding', encoding)
        data_only = merged_config.get('data_only', data_only)
        schema = tuple(merged_config.get('schema', schema)) if merged_config.get('schema') else schema
        sample_schema = merged_config.get('sample_schema', sample_schema)
        use_staging = merged_config.get('use_staging', use_staging)
        no_staging = merged_config.get('no_staging', no_staging)
        force = merged_config.get('force', force)
        keep = merged_config.get('keep', keep)
        exclude_table = tuple(merged_config.get('exclude_table', exclude_table)) if merged_config.get('exclude_table') else exclude_table
        exclude_schema = tuple(merged_config.get('exclude_schema', exclude_schema)) if merged_config.get('exclude_schema') else exclude_schema
        exclude_column = tuple(merged_config.get('exclude_column', exclude_column)) if merged_config.get('exclude_column') else exclude_column
        dry_run = merged_config.get('dry_run', dry_run)
        verify = merged_config.get('verify', verify)
        self_test = merged_config.get('self_test', self_test)
        log_level = merged_config.get('log_level', log_level)
        log_file = merged_config.get('log_file', log_file)
        audit_file = merged_config.get('audit_file', audit_file)
        target_version = merged_config.get('target_version', target_version)
        verbose = merged_config.get('verbose', verbose)
        trace = merged_config.get('trace', trace)
    
    # Configure logging
    log_level_enum = parse_log_level(log_level)
    if verbose:
        log_level_enum = LogLevel.INFO if log_level_enum == LogLevel.ERROR else log_level_enum
    
    logger = Logger()
    logger.configure(level=log_level_enum, log_file=log_file)
    
    if config:
        logger.info(f"Loaded configuration from: {config}")
    
    try:
        # Validate options
        if ordered_asc and ordered_desc:
            logger.error("Cannot specify both --ordered-asc and --ordered-desc")
            sys.exit(EXIT_CONFIG_ERROR)
        
        if ordered_asc:
            ordered_desc = False
        
        if not dbname and not connection_uri:
            dbname = os.getenv("PGDATABASE") or os.getenv("USER")
            if not dbname:
                logger.error("Database name must be specified via --dbname, --connection-uri, or PGDATABASE environment variable")
                sys.exit(EXIT_CONFIG_ERROR)
        
        # Parse limit rules
        limit_rules = []
        if limit:
            limit_rules = parse_limit_rules(list(limit))
        
        # Connect to database (needed for both normal and dry-run modes)
        logger.info("Connecting to database...")
        try:
            db_conn = DatabaseConnection(
                host=host,
                port=port,
                dbname=dbname,
                username=username,
                password=password,
                connection_uri=connection_uri,
                ssl_mode=ssl_mode,
                ssl_cert=ssl_cert,
                ssl_key=ssl_key,
                ssl_ca=ssl_ca,
            )
            
            with db_conn.connect() as conn:
                # Enable autocommit mode so each operation is independent
                # This prevents transaction abort errors from affecting subsequent operations
                conn.autocommit = True
                
                # Set session-level transaction isolation (applies to all future transactions)
                # Using SESSION instead of TRANSACTION so it persists across operations
                with conn.cursor() as cur:
                    cur.execute("SET SESSION CHARACTERISTICS AS TRANSACTION ISOLATION LEVEL REPEATABLE READ")
                
                logger.info("Connected successfully")
                
                # Discover schema
                logger.info("Discovering database schema...")
                if verbose:
                    if schema:
                        logger.info(f"  Filtering schemas: {', '.join(schema)}")
                    if exclude_schema:
                        logger.info(f"  Excluding schemas: {', '.join(exclude_schema)}")
                    if exclude_table:
                        logger.info(f"  Excluding tables: {', '.join(exclude_table)}")
                    if exclude_column:
                        logger.info(f"  Excluding columns: {', '.join(exclude_column)}")
                
                discovery = SchemaDiscovery(conn)
                
                schemas_list = list(schema) if schema else None
                exclude_schemas_list = list(exclude_schema) if exclude_schema else None
                exclude_tables_list = list(exclude_table) if exclude_table else None
                exclude_columns_list = list(exclude_column) if exclude_column else None
                
                tables = discovery.get_tables(
                    schemas=schemas_list,
                    exclude_schemas=exclude_schemas_list,
                    exclude_tables=exclude_tables_list,
                )
                
                logger.info(f"Found {len(tables)} tables")
                if verbose and tables:
                    # Group by schema
                    from collections import defaultdict
                    schema_counts = defaultdict(int)
                    for table in tables:
                        schema_counts[table.schema] += 1
                    for schema_name, count in sorted(schema_counts.items()):
                        logger.info(f"  Schema '{schema_name}': {count} table(s)")
                
                # Validate limit patterns match at least one table
                if limit_rules:
                    if verbose:
                        logger.info(f"Validating {len(limit_rules)} limit rule(s)...")
                    
                    unmatched_rules = []
                    matched_rules = []
                    for rule in limit_rules:
                        rule_matched = False
                        matched_tables = []
                        for table in tables:
                            qualified = table.qualified_name
                            unqualified = table.name
                            schema_pattern = f"{table.schema}.*"
                            
                            if (rule.compiled_pattern.match(qualified) or
                                rule.compiled_pattern.match(unqualified) or
                                rule.compiled_pattern.match(schema_pattern)):
                                rule_matched = True
                                matched_tables.append(table.qualified_name)
                        
                        if rule_matched:
                            matched_rules.append((rule.pattern, matched_tables))
                            if verbose:
                                limit_desc = f"{rule.limit_type.value}"
                                if rule.limit_type.value != "full":
                                    limit_desc += f"={rule.value}"
                                logger.info(f"  Pattern '{rule.pattern}' ({limit_desc}): matches {len(matched_tables)} table(s)")
                        else:
                            unmatched_rules.append(rule.pattern)
                    
                    if unmatched_rules:
                        logger.warning(
                            f"Limit pattern(s) matched zero tables: {', '.join(unmatched_rules)}. "
                            f"These patterns will have no effect."
                        )
                
                # Get additional database objects
                if verbose:
                    logger.info("Discovering additional database objects...")
                schema_objects = discovery.get_database_objects(
                    schemas=schemas_list,
                    exclude_schemas=exclude_schemas_list,
                )
                
                if verbose:
                    obj_counts = {
                        "types": len(schema_objects.get("types", [])),
                        "sequences": len(schema_objects.get("sequences", [])),
                        "views": len(schema_objects.get("views", [])),
                        "materialized_views": len(schema_objects.get("materialized_views", [])),
                        "functions": len(schema_objects.get("functions", [])),
                        "extensions": len(schema_objects.get("extensions", [])),
                    }
                    logger.info("  Database objects found:")
                    for obj_type, count in obj_counts.items():
                        if count > 0:
                            logger.info(f"    {obj_type}: {count}")
                
                # Resolve dependencies
                logger.info("Resolving table dependencies...")
                resolver = DependencyResolver(tables)
                
                if resolver.has_circular_dependencies():
                    circular_groups = resolver.get_circular_groups()
                    logger.warning(f"Detected {len(circular_groups)} circular dependency group(s)")
                    if verbose:
                        for group in circular_groups:
                            logger.info(f"  Circular dependency: {' -> '.join(group)}")
                    else:
                        for group in circular_groups:
                            logger.debug(f"Circular dependency: {' -> '.join(group)}")
                elif verbose:
                    logger.info("  No circular dependencies detected")
                
                # Constants for staging mode auto-detection
                STAGING_THRESHOLD_TABLES = 50
                STAGING_THRESHOLD_FKS = 5
                
                # Determine if staging should be used
                # Mitigation: Make it optional and intelligent
                use_staging_flag = False
                staging_manager = None
                
                # Explicit flags take precedence
                if no_staging:
                    use_staging_flag = False
                    logger.info("Staging mode explicitly disabled")
                elif use_staging:
                    use_staging_flag = True
                    logger.info("Staging mode explicitly enabled")
                else:
                    # Auto-detect: Use staging for large/complex databases
                    # Heuristic: > STAGING_THRESHOLD_TABLES tables or complex FK relationships
                    total_tables = len(tables)
                    has_complex_fks = any(
                        len(table.foreign_keys) > STAGING_THRESHOLD_FKS for table in tables
                    )
                    
                    if total_tables > STAGING_THRESHOLD_TABLES or has_complex_fks:
                        logger.info(
                            f"Large/complex database detected ({total_tables} tables) - "
                            "considering staging mode for better performance"
                        )
                        use_staging_flag = True
                    else:
                        logger.debug("Using direct query mode (small database)")
                
                use_staging = use_staging_flag
                
                # Handle dry-run mode
                if dry_run:
                    logger.info("=" * 70)
                    logger.info("DRY-RUN MODE: Showing what would be sampled")
                    logger.info("=" * 70)
                    logger.info("")
                    
                    # Get table row counts
                    logger.info("Fetching table row counts...")
                    table_counts = {}
                    try:
                        with conn.cursor() as cur:
                            # Use pg_stat_user_tables for fast approximate counts
                            # Fall back to COUNT(*) if stats are not available
                            for table in tables:
                                qualified = f'"{table.schema}"."{table.name}"'
                                try:
                                    # Try pg_stat_user_tables first (fast, approximate)
                                    cur.execute("""
                                        SELECT n_live_tup 
                                        FROM pg_stat_user_tables 
                                        WHERE schemaname = %s AND relname = %s
                                    """, (table.schema, table.name))
                                    row = cur.fetchone()
                                    if row and row[0] is not None:
                                        table_counts[table.qualified_name] = row[0]
                                    else:
                                        # Fall back to COUNT(*) (slower, exact)
                                        cur.execute(f'SELECT COUNT(*) FROM {qualified}')
                                        table_counts[table.qualified_name] = cur.fetchone()[0]
                                except Exception as e:
                                    logger.debug(f"Could not get count for {table.qualified_name}: {e}")
                                    table_counts[table.qualified_name] = None
                    except Exception as e:
                        logger.warning(f"Could not fetch table counts: {e}")
                    
                    # Calculate what would be sampled
                    logger.info("")
                    logger.info("Sampling Plan:")
                    logger.info("-" * 70)
                    
                    total_source_rows = 0
                    total_sampled_rows = 0
                    tables_with_limits = []
                    
                    # Create a temporary sampling engine to use its helper methods
                    temp_engine = SamplingEngine(
                        conn=conn,
                        tables=tables,
                        resolver=resolver,
                        limit_rules=limit_rules,
                        ordered=ordered,
                        ordered_desc=ordered_desc,
                        random=random,
                        exclude_columns=exclude_columns_list,
                        use_staging=False,
                        staging_manager=None,
                        logger=logger,
                        verbose=False,
                    )
                    
                    for table in tables:
                        source_count = table_counts.get(table.qualified_name, 0) or 0
                        total_source_rows += source_count
                        
                        limit_rule = temp_engine._find_limit_rule(table)
                        estimated_count = 0
                        limit_desc = "default (100)"
                        
                        if limit_rule:
                            if limit_rule.limit_type.value == 'full':
                                estimated_count = source_count
                                limit_desc = "* (all rows)"
                            elif limit_rule.limit_type.value == 'percentage':
                                estimated_count = max(1, int(source_count * limit_rule.value / 100))
                                pct_value = limit_rule.value
                                if isinstance(pct_value, float) and pct_value.is_integer():
                                    limit_desc = f"{int(pct_value)}%"
                                else:
                                    limit_desc = f"{pct_value}%"
                            elif limit_rule.limit_type.value == 'conditional':
                                # For conditional, we can't estimate without running the query
                                # Show the condition instead
                                limit_desc = f"WHERE {limit_rule.value}"
                                estimated_count = None  # Unknown
                            else:  # numeric
                                estimated_count = min(limit_rule.value, source_count)
                                limit_desc = str(limit_rule.value)
                        else:
                            estimated_count = min(100, source_count)
                        
                        if estimated_count is not None:
                            total_sampled_rows += estimated_count
                        
                        tables_with_limits.append({
                            'table': table.qualified_name,
                            'source': source_count,
                            'estimated': estimated_count,
                            'limit': limit_desc,
                        })
                    
                    # Display table-by-table breakdown
                    logger.info(f"{'Table':<50} {'Source Rows':>12} {'Limit':<20} {'Est. Sampled':>12}")
                    logger.info("-" * 70)
                    
                    for item in tables_with_limits:
                        source_str = f"{item['source']:,}" if item['source'] else "N/A"
                        if item['estimated'] is not None:
                            est_str = f"{item['estimated']:,}"
                        else:
                            est_str = "? (conditional)"
                        logger.info(f"{item['table']:<50} {source_str:>12} {item['limit']:<20} {est_str:>12}")
                    
                    logger.info("-" * 70)
                    logger.info(f"{'TOTAL':<50} {total_source_rows:>12,} {'':<20} {total_sampled_rows:>12,}")
                    logger.info("")
                    
                    # Show additional info
                    logger.info("Configuration:")
                    logger.info(f"  Mode: {'staging' if use_staging else 'direct'}")
                    if ordered:
                        logger.info(f"  Ordering: {'descending' if ordered_desc else 'ascending'}")
                    if random:
                        logger.info("  Random sampling: enabled")
                    if exclude_columns_list:
                        logger.info(f"  Excluded columns: {', '.join(exclude_columns_list)}")
                    if exclude_tables_list:
                        logger.info(f"  Excluded tables: {', '.join(exclude_tables_list)}")
                    if exclude_schemas_list:
                        logger.info(f"  Excluded schemas: {', '.join(exclude_schemas_list)}")
                    
                    logger.info("")
                    logger.info("=" * 70)
                    logger.info("DRY-RUN complete. No data was sampled or exported.")
                    logger.info("Remove --dry-run flag to perform actual sampling.")
                    logger.info("=" * 70)
                    
                    sys.exit(EXIT_SUCCESS)
                
                # Try to create staging schema if needed
                if use_staging:
                    logger.info("Attempting to use staging schema for improved performance...")
                    staging_manager = StagingManager(conn, sample_schema, logger)
                    if staging_manager.create_schema(force=force):
                        logger.info("Staging schema created successfully")
                    else:
                        logger.warning("Could not create staging schema - falling back to direct query mode")
                        use_staging = False
                        staging_manager = None
                
                # Sample data
                if use_staging:
                    logger.info("Sampling data using staging schema...")
                else:
                    logger.info("Sampling data directly from source tables...")
                
                sampling_engine = SamplingEngine(
                    conn=conn,
                    tables=tables,
                    resolver=resolver,
                    limit_rules=limit_rules,
                    ordered=ordered,
                    ordered_desc=ordered_desc,
                    random=random,
                    exclude_columns=exclude_columns_list,
                    use_staging=use_staging,
                    staging_manager=staging_manager,
                    logger=logger,
                    verbose=verbose,
                )
                
                try:
                    start_time = time.time()
                    results = sampling_engine.sample_all()
                    elapsed_time = time.time() - start_time
                    total_rows = sum(r.row_count for r in results.values())
                    logger.info(f"Sampled {total_rows} rows across {len(results)} tables in {elapsed_time:.2f} seconds")
                    if verbose:
                        logger.info(f"  Average: {total_rows / len(results):.1f} rows per table" if results else "  No rows sampled")
                finally:
                    # Cleanup staging schema unless --keep is specified
                    # This runs even if sampling fails, ensuring cleanup happens
                    if use_staging and staging_manager and not keep:
                        staging_manager.drop_schema()
                    elif use_staging and staging_manager and keep:
                        logger.info(f"Staging schema '{sample_schema}' preserved (--keep flag)")
                
                # If we get here, sampling succeeded - continue with output generation
                
                # Verify referential integrity if requested
                if verify:
                    logger.info("")
                    logger.info("=" * 70)
                    logger.info("Verifying referential integrity...")
                    logger.info("=" * 70)
                    is_valid, violations = sampling_engine.verify_referential_integrity()
                    
                    if is_valid:
                        logger.info("")
                        logger.info("✓ Referential integrity check passed: No violations found")
                        logger.info("=" * 70)
                    else:
                        logger.error("")
                        logger.error("✗ Referential integrity check FAILED: Found violations")
                        logger.error("")
                        logger.error("Violations:")
                        logger.error("-" * 70)
                        
                        for i, violation in enumerate(violations, 1):
                            logger.error(f"{i}. Constraint: {violation['table']}.{violation['constraint']}")
                            logger.error(f"   Foreign Key: {violation['table']}({', '.join(violation['columns'])})")
                            logger.error(f"   References: {violation['referenced_table']}({', '.join(violation['referenced_columns'])})")
                            logger.error(f"   Violations: {violation['violation_count']} FK value(s) not found in referenced table")
                            
                            if violation['sample_violations']:
                                sample_str = ", ".join(str(v) for v in violation['sample_violations'][:5])
                                if violation['violation_count'] > 5:
                                    sample_str += f" ... and {violation['violation_count'] - 5} more"
                                logger.error(f"   Sample values: {sample_str}")
                            logger.error("")
                        
                        logger.error("=" * 70)
                        logger.error("Referential integrity verification failed. The sampled data contains")
                        logger.error("foreign key violations that would cause import errors.")
                        logger.error("")
                        
                        # Cleanup staging schema before exiting
                        if use_staging and staging_manager and not keep:
                            staging_manager.drop_schema()
                        
                        sys.exit(EXIT_INTEGRITY_ERROR)
                
                # Generate output
                logger.info("Generating SQL output...")
                if verbose:
                    logger.info(f"  Output mode: {'data-only' if data_only else 'schema + data'}")
                    if file:
                        logger.info(f"  Output file: {file}")
                    else:
                        logger.info("  Output destination: stdout")
                    if target_version:
                        logger.info(f"  Target PostgreSQL version: {target_version}")
                
                # Prepare export metadata for header
                export_metadata = {
                    "dbname": dbname,
                    "host": host,
                    "data_only": data_only,
                    "target_version": target_version,
                }
                
                # Add limit rules info
                if limit_rules:
                    limit_strs = []
                    for rule in limit_rules:
                        if rule.limit_type.value == 'full':
                            limit_strs.append(f"{rule.pattern}=*")
                        elif rule.limit_type.value == 'percentage':
                            # Format percentage: show as integer if whole number, otherwise show decimal
                            pct_value = rule.value
                            if isinstance(pct_value, float) and pct_value.is_integer():
                                limit_strs.append(f"{rule.pattern}={int(pct_value)}%")
                            else:
                                limit_strs.append(f"{rule.pattern}={pct_value}%")
                        elif rule.limit_type.value == 'conditional':
                            limit_strs.append(f"{rule.pattern}={rule.value}")
                        else:  # numeric
                            limit_strs.append(f"{rule.pattern}={rule.value}")
                    export_metadata["limit_rules"] = limit_strs
                
                # Add ordering info
                if ordered:
                    export_metadata["ordered"] = True
                    export_metadata["ordered_desc"] = ordered_desc
                
                # Add random sampling info
                if random:
                    export_metadata["random"] = True
                
                # Add exclusion info
                if exclude_schema:
                    export_metadata["exclude_schemas"] = list(exclude_schema)
                if exclude_table:
                    export_metadata["exclude_tables"] = list(exclude_table)
                if exclude_column:
                    export_metadata["exclude_columns"] = list(exclude_column)
                
                output_gen = SQLOutputGenerator(
                    conn=conn,
                    tables=tables,
                    results=results,
                    resolver=resolver,
                    schema_objects=schema_objects,
                    data_only=data_only,
                    target_version=target_version,
                    logger=logger,
                    verbose=verbose,
                    export_metadata=export_metadata,
                    exclude_columns=exclude_columns_list,
                )
                
                # Determine output destination
                # For self-test, we need a file (create temp file if outputting to stdout)
                temp_sql_file = None
                if self_test and not file:
                    # Create temporary file for self-test
                    import tempfile
                    temp_fd, temp_sql_file = tempfile.mkstemp(suffix='.sql', prefix='dbsample_test_')
                    os.close(temp_fd)
                    file = temp_sql_file
                    logger.info(f"Created temporary SQL file for self-test: {temp_sql_file}")
                
                # Determine if compression should be used
                use_compression = compress
                if file and file.endswith('.gz'):
                    use_compression = True
                
                # Auto-append .gz extension if compression is enabled but extension is missing
                original_file = file
                if file and use_compression and not file.endswith('.gz'):
                    file = file + '.gz'
                    if verbose:
                        logger.info(f"  Auto-appending .gz extension: {original_file} -> {file}")
                
                if file:
                    # Open file with or without compression
                    if use_compression:
                        output_file = gzip.open(file, "wt", encoding=encoding or "utf-8")
                        if verbose:
                            logger.info(f"  Compression: gzip enabled")
                    else:
                        output_file = open(file, "w", encoding=encoding or "utf-8")
                    
                    output = output_file
                else:
                    output = sys.stdout
                    if compress:
                        logger.warning("Compression requested but output is to stdout - compression disabled")
                
                try:
                    output_start = time.time()
                    output_gen.generate(output, encoding=encoding or "utf-8")
                    output_elapsed = time.time() - output_start
                    logger.info("SQL output generated successfully")
                    if verbose:
                        logger.info(f"  Output generation took {output_elapsed:.2f} seconds")
                finally:
                    if file and output != sys.stdout:
                        output.close()
                        # Set restrictive permissions after file is closed
                        try:
                            os.chmod(file, stat.S_IRUSR | stat.S_IWUSR)  # 600
                        except Exception as e:
                            if verbose:
                                logger.debug(f"  Could not set file permissions: {e}")
                        
                        if verbose:
                            file_size = os.path.getsize(file)
                            size_mb = file_size / (1024 * 1024)
                            compression_note = " (compressed)" if use_compression else ""
                            logger.info(f"  Output file size: {size_mb:.2f} MB ({file_size:,} bytes){compression_note}")
                
                # Run self-test if requested
                if self_test:
                    logger.info("")
                    logger.info("=" * 70)
                    logger.info("SELF-TEST MODE: End-to-end validation")
                    logger.info("=" * 70)
                    logger.info("")
                    
                    # Prepare connection parameters for self-test
                    conn_params = {
                        "host": host,
                        "port": port,
                        "username": username,
                        "password": password,
                        "connection_uri": connection_uri,
                        "ssl_mode": ssl_mode,
                        "ssl_cert": ssl_cert,
                        "ssl_key": ssl_key,
                        "ssl_ca": ssl_ca,
                    }
                    
                    # Create self-test runner
                    test_runner = SelfTestRunner(
                        source_conn_params=conn_params,
                        logger=logger,
                        verbose=verbose,
                    )
                    
                    # Track temp file for cleanup
                    if temp_sql_file:
                        test_runner.set_temp_sql_file(temp_sql_file)
                    
                    # Run test
                    success, test_results = test_runner.run_test(sql_file=file)
                    
                    # Report results
                    logger.info("")
                    if success:
                        logger.info("=" * 70)
                        logger.info("✓ SELF-TEST PASSED: All checks passed successfully")
                        logger.info("=" * 70)
                    else:
                        logger.error("=" * 70)
                        logger.error("✗ SELF-TEST FAILED")
                        logger.error("=" * 70)
                        
                        if test_results.get("errors"):
                            logger.error("")
                            logger.error("Errors:")
                            for error in test_results["errors"]:
                                logger.error(f"  - {error}")
                        
                        if test_results.get("violations"):
                            logger.error("")
                            logger.error("Constraint Violations:")
                            for violation in test_results["violations"]:
                                logger.error(f"  - {violation['table']}.{violation['constraint']}: "
                                           f"Invalid foreign key to {violation['referenced_table']}")
                        
                        logger.error("")
                        
                        # Cleanup staging schema before exiting
                        if use_staging and staging_manager and not keep:
                            staging_manager.drop_schema()
                        
                        sys.exit(EXIT_INTEGRITY_ERROR)
                
                # Write audit trail if requested
                if audit_file:
                    audit_data = {
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "database": dbname,
                        "host": host,
                        "port": port,
                        "tables_sampled": len(results),
                        "total_rows": total_rows,
                        "tables": [
                            {
                                "schema": r.table_schema,
                                "name": r.table_name,
                                "rows": r.row_count,
                            }
                            for r in results.values()
                        ],
                    }
                    import json
                    with open(audit_file, "w") as f:
                        json.dump(audit_data, f, indent=2)
                    logger.info(f"Audit trail written to {audit_file}")
                
        except psycopg.OperationalError as e:
            logger.error(f"Database connection error: {e}")
            sys.exit(EXIT_CONNECTION_ERROR)
        except psycopg.errors.InsufficientPrivilege as e:
            logger.error(f"Permission denied: {e}")
            sys.exit(EXIT_PERMISSION_ERROR)
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            sys.exit(EXIT_GENERAL_ERROR)
    
    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
        sys.exit(EXIT_GENERAL_ERROR)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(EXIT_GENERAL_ERROR)


if __name__ == "__main__":
    main()

