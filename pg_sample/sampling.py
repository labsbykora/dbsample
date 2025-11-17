"""Data sampling logic with limit patterns and constraint resolution."""

import re
from typing import List, Dict, Set, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import psycopg
from pg_sample.schema import Table, ForeignKey
from pg_sample.dependencies import DependencyResolver
from pg_sample.logger import Logger


class LimitType(Enum):
    """Limit rule type."""
    NUMERIC = "numeric"
    PERCENTAGE = "percentage"
    FULL = "full"
    CONDITIONAL = "conditional"


@dataclass
class LimitRule:
    """Limit rule definition."""
    pattern: str
    limit_type: LimitType
    value: Any  # int for numeric/percentage, str for conditional
    compiled_pattern: re.Pattern


@dataclass
class SamplingResult:
    """Result of sampling operation."""
    table_schema: str
    table_name: str
    rows: List[Tuple]
    row_count: int
    limit_applied: Optional[LimitRule] = None


class SamplingEngine:
    """Engine for sampling data from tables."""
    
    def __init__(
        self,
        conn: psycopg.Connection,
        tables: List[Table],
        resolver: DependencyResolver,
        limit_rules: List[LimitRule],
        ordered: bool = False,
        ordered_desc: bool = True,
        random: bool = False,
        exclude_columns: Optional[List[str]] = None,
        use_staging: bool = False,
        staging_manager: Optional['StagingManager'] = None,
        logger: Optional[Logger] = None,
        verbose: bool = False,
    ):
        """Initialize sampling engine.
        
        Args:
            conn: Database connection
            tables: List of tables to sample
            resolver: Dependency resolver
            limit_rules: List of limit rules to apply
            ordered: Enable deterministic ordering
            ordered_desc: Use descending order (when ordered=True)
            random: Use random row selection
            exclude_columns: List of column exclusion patterns
            use_staging: Whether to use staging schema
            staging_manager: Staging manager instance
            logger: Logger instance for progress messages
            verbose: Enable verbose progress logging
        """
        self.conn = conn
        self.tables = {t.qualified_name: t for t in tables}
        self.resolver = resolver
        self.limit_rules = limit_rules
        self.ordered = ordered
        self.ordered_desc = ordered_desc
        self.random = random
        self.exclude_columns = exclude_columns or []
        self.use_staging = use_staging
        self.staging_manager = staging_manager
        self.logger = logger or Logger()
        self.verbose = verbose
        self.sampled_rows: Dict[str, Set[Tuple]] = {}  # table -> set of row identifiers
        self.results: Dict[str, SamplingResult] = {}
    
    def sample_all(self) -> Dict[str, SamplingResult]:
        """Sample all tables in dependency order.
        
        Returns:
            Dictionary mapping table names to sampling results
        """
        if self.use_staging and self.staging_manager:
            return self._sample_with_staging()
        else:
            return self._sample_direct()
    
    def _sample_direct(self) -> Dict[str, SamplingResult]:
        """Sample directly from source tables (original method)."""
        insertion_order = self.resolver.get_insertion_order()
        total_tables = len([t for t in insertion_order if t in self.tables])
        
        if self.verbose:
            self.logger.info(f"Starting direct sampling for {total_tables} tables...")
        else:
            # Show simple progress for non-verbose mode
            self.logger.info(f"Sampling {total_tables} tables...")
        
        for idx, table_name in enumerate(insertion_order, 1):
            if table_name not in self.tables:
                continue
            
            table = self.tables[table_name]
            
            if self.verbose:
                # Show detailed progress with percentage
                percentage = int((idx / total_tables) * 100)
                progress_bar = self._get_progress_bar(idx, total_tables)
                self.logger.info(f"[{idx}/{total_tables}] {progress_bar} {percentage}% - Sampling table: {table_name}")
            else:
                # Show simple progress
                percentage = int((idx / total_tables) * 100)
                progress_bar = self._get_progress_bar(idx, total_tables)
                self.logger.info(f"[{idx}/{total_tables}] {progress_bar} {percentage}% - {table_name}")
            
            try:
                limit_rule = self._find_limit_rule(table)
                if self.verbose:
                    if limit_rule:
                        if limit_rule.limit_type == LimitType.PERCENTAGE:
                            # Format percentage: show as integer if whole number, otherwise show decimal
                            pct_value = limit_rule.value
                            if isinstance(pct_value, float) and pct_value.is_integer():
                                limit_str = f" (limit: {int(pct_value)}%)"
                            else:
                                limit_str = f" (limit: {pct_value}%)"
                        elif limit_rule.limit_type == LimitType.FULL:
                            limit_str = " (limit: *)"
                        elif limit_rule.limit_type == LimitType.CONDITIONAL:
                            limit_str = f" (limit: {limit_rule.value})"
                        else:  # NUMERIC
                            limit_str = f" (limit: {limit_rule.value})"
                    else:
                        limit_str = ""
                    self.logger.info(f"  Querying data{limit_str}...")
                
                result = self._sample_table(table)
                self.results[table_name] = result
                
                if self.verbose:
                    self.logger.info(f"  ✓ Sampled {result.row_count} rows from {table_name}")
                
                # Store row identifiers for FK resolution
                if table.has_primary_key:
                    pk_indices = [i for i, col in enumerate(table.columns) if col["name"] in table.primary_key]
                    self.sampled_rows[table_name] = {
                        tuple(row[i] for i in pk_indices)
                        for row in result.rows
                    }
            except Exception as e:
                if self.verbose:
                    self.logger.error(f"  ✗ Failed to sample {table_name}: {e}")
                raise RuntimeError(
                    f"Failed to sample table '{table_name}': {e}. "
                    f"Stopping to maintain referential integrity."
                ) from e
        
        # Resolve foreign key dependencies
        if self.verbose:
            self.logger.info("Resolving foreign key dependencies...")
        try:
            self._resolve_foreign_keys()
            if self.verbose:
                self.logger.info("  ✓ Foreign key dependencies resolved")
        except Exception as e:
            if self.verbose:
                self.logger.error(f"  ✗ Failed to resolve foreign keys: {e}")
            raise RuntimeError(
                f"Failed to resolve foreign key dependencies: {e}. "
                f"Stopping to maintain referential integrity."
            ) from e
        
        if self.verbose:
            total_rows = sum(r.row_count for r in self.results.values())
            self.logger.info(f"✓ Direct sampling complete: {total_rows} total rows across {len(self.results)} tables")
        
        return self.results
    
    def _sample_with_staging(self) -> Dict[str, SamplingResult]:
        """Sample using staging schema for better performance and validation.
        
        Note: With autocommit mode, each operation is independent. If one fails,
        it won't affect others, but we fail-fast to maintain referential integrity.
        Partial exports would break foreign key constraints.
        """
        insertion_order = self.resolver.get_insertion_order()
        total_tables = len([t for t in insertion_order if t in self.tables])
        failed_tables = []
        
        if self.verbose:
            self.logger.info(f"Starting staging sampling for {total_tables} tables...")
        else:
            # Show simple progress for non-verbose mode
            self.logger.info(f"Sampling {total_tables} tables (staging mode)...")
        
        # First pass: Sample data into staging tables
        for idx, table_name in enumerate(insertion_order, 1):
            if table_name not in self.tables:
                continue
            
            table = self.tables[table_name]
            
            if self.verbose:
                # Show detailed progress with percentage
                percentage = int((idx / total_tables) * 100)
                progress_bar = self._get_progress_bar(idx, total_tables)
                self.logger.info(f"[{idx}/{total_tables}] {progress_bar} {percentage}% - Processing table: {table_name}")
            else:
                # Show simple progress
                percentage = int((idx / total_tables) * 100)
                progress_bar = self._get_progress_bar(idx, total_tables)
                self.logger.info(f"[{idx}/{total_tables}] {progress_bar} {percentage}% - {table_name}")
            
            try:
                # Create staging table
                if self.verbose:
                    self.logger.info(f"  Creating staging table...")
                staging_table = self.staging_manager.create_staging_table(
                    table.schema,
                    table.name,
                    table.columns,
                )
                
                # Build query and copy to staging
                limit_rule = self._find_limit_rule(table)
                query, params = self._build_query(table, limit_rule)
                
                if self.verbose:
                    if limit_rule:
                        if limit_rule.limit_type == LimitType.PERCENTAGE:
                            # Format percentage: show as integer if whole number, otherwise show decimal
                            pct_value = limit_rule.value
                            if isinstance(pct_value, float) and pct_value.is_integer():
                                limit_str = f" (limit: {int(pct_value)}%)"
                            else:
                                limit_str = f" (limit: {pct_value}%)"
                        elif limit_rule.limit_type == LimitType.FULL:
                            limit_str = " (limit: *)"
                        elif limit_rule.limit_type == LimitType.CONDITIONAL:
                            limit_str = f" (limit: {limit_rule.value})"
                        else:  # NUMERIC
                            limit_str = f" (limit: {limit_rule.value})"
                    else:
                        limit_str = ""
                    self.logger.info(f"  Sampling data{limit_str}...")
                
                # The query from _build_query is a full SELECT statement
                # Pass it directly to copy_data_to_staging which will wrap it in INSERT INTO
                row_count = self.staging_manager.copy_data_to_staging(
                    table.schema,
                    table.name,
                    staging_table,
                    query,
                    params,
                )
                
                if self.verbose:
                    self.logger.info(f"  ✓ Sampled {row_count} rows from {table_name}")
                
                # Create indexes on staging table for FK resolution
                if table.indexes:
                    if self.verbose:
                        self.logger.info(f"  Creating {len(table.indexes)} index(es)...")
                    self.staging_manager.create_staging_indexes(table.name, table.indexes)
            except Exception as e:
                # Track failed tables but fail-fast to maintain integrity
                # A partial export would break foreign key constraints
                failed_tables.append((table_name, str(e)))
                if self.verbose:
                    self.logger.error(f"  ✗ Failed to sample {table_name}: {e}")
                # Re-raise to stop the process - we can't have a valid partial export
                raise RuntimeError(
                    f"Failed to sample table '{table_name}': {e}. "
                    f"Stopping to maintain referential integrity. "
                    f"Partial exports would break foreign key constraints."
                ) from e
        
        # Second pass: Resolve foreign key dependencies in staging
        if self.verbose:
            self.logger.info("Resolving foreign key dependencies...")
        try:
            self._resolve_foreign_keys_staging()
            if self.verbose:
                self.logger.info("  ✓ Foreign key dependencies resolved")
        except Exception as e:
            if self.verbose:
                self.logger.error(f"  ✗ Failed to resolve foreign keys: {e}")
            raise RuntimeError(
                f"Failed to resolve foreign key dependencies: {e}. "
                f"Stopping to maintain referential integrity."
            ) from e
        
        # Third pass: Read final data from staging
        if self.verbose:
            self.logger.info(f"Reading final data from staging ({total_tables} tables)...")
        else:
            self.logger.info(f"Reading final data from staging...")
        for idx, table_name in enumerate(insertion_order, 1):
            if table_name not in self.tables:
                continue
            
            table = self.tables[table_name]
            try:
                if self.verbose:
                    percentage = int((idx / total_tables) * 100)
                    progress_bar = self._get_progress_bar(idx, total_tables)
                    self.logger.info(f"  [{idx}/{total_tables}] {progress_bar} {percentage}% - Reading {table_name}...")
                else:
                    percentage = int((idx / total_tables) * 100)
                    progress_bar = self._get_progress_bar(idx, total_tables)
                    self.logger.info(f"[{idx}/{total_tables}] {progress_bar} {percentage}% - {table_name}")
                columns = [col["name"] for col in table.columns]
                rows = self.staging_manager.get_staging_data(table.name, columns)
                
                limit_rule = self._find_limit_rule(table)
                self.results[table_name] = SamplingResult(
                    table_schema=table.schema,
                    table_name=table.name,
                    rows=rows,
                    row_count=len(rows),
                    limit_applied=limit_rule,
                )
                if self.verbose:
                    self.logger.info(f"  ✓ Read {len(rows)} rows from {table_name}")
            except Exception as e:
                if self.verbose:
                    self.logger.error(f"  ✗ Failed to read {table_name}: {e}")
                raise RuntimeError(
                    f"Failed to read staging data for table '{table_name}': {e}. "
                    f"Stopping to maintain referential integrity."
                ) from e
        
        if self.verbose:
            total_rows = sum(r.row_count for r in self.results.values())
            self.logger.info(f"✓ Staging sampling complete: {total_rows} total rows across {len(self.results)} tables")
        
        return self.results
    
    def _resolve_foreign_keys_staging(self):
        """Resolve foreign key dependencies using staging tables."""
        # Similar to _resolve_foreign_keys but queries staging tables
        # This allows for more efficient FK resolution with indexes
        for table_name, table in self.tables.items():
            if table_name not in self.results:
                continue
            
            for fk in table.foreign_keys:
                ref_table = f"{fk.referenced_schema}.{fk.referenced_table}"
                if ref_table not in self.tables:
                    continue
                
                ref_table_obj = self.tables[ref_table]
                if not ref_table_obj.has_primary_key:
                    continue
                
                # Query staging tables to find missing FK references
                with self.conn.cursor() as cur:
                    # Get referenced values from staging
                    ref_col_indices = [
                        i for i, col in enumerate(table.columns)
                        if col["name"] in fk.columns
                    ]
                    
                    # Find missing references
                    cols = ", ".join(f'"{col}"' for col in fk.columns)
                    ref_cols = ", ".join(f'"{col}"' for col in fk.referenced_columns)
                    
                    cur.execute(f"""
                        SELECT DISTINCT {cols}
                        FROM {self.staging_manager.schema_name}."{table.name}" t
                        WHERE ({cols}) IS NOT NULL
                        AND NOT EXISTS (
                            SELECT 1
                            FROM {self.staging_manager.schema_name}."{fk.referenced_table}" r
                            WHERE ({cols}) = ({ref_cols})
                        )
                    """)
                    
                    missing_refs = cur.fetchall()
                    
                    if missing_refs:
                        # Fetch missing rows from source and insert into staging
                        for ref_values in missing_refs:
                            ref_cols_where = " AND ".join(
                                f'"{col}" = %s' for col in fk.referenced_columns
                            )
                            
                            cur.execute(f"""
                                INSERT INTO {self.staging_manager.schema_name}."{fk.referenced_table}"
                                SELECT * FROM "{fk.referenced_schema}"."{fk.referenced_table}"
                                WHERE {ref_cols_where}
                                LIMIT 1
                            """, ref_values)
                        
                        self.conn.commit()
    
    def _sample_table(self, table: Table) -> SamplingResult:
        """Sample a single table.
        
        Args:
            table: Table to sample
            
        Returns:
            SamplingResult
        """
        # Find matching limit rule
        limit_rule = self._find_limit_rule(table)
        
        # Build query
        query, params = self._build_query(table, limit_rule)
        
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
        
        return SamplingResult(
            table_schema=table.schema,
            table_name=table.name,
            rows=rows,
            row_count=len(rows),
            limit_applied=limit_rule,
        )
    
    def _find_limit_rule(self, table: Table) -> Optional[LimitRule]:
        """Find matching limit rule for table.
        
        Args:
            table: Table to find rule for
            
        Returns:
            Matching LimitRule or None
        """
        qualified = table.qualified_name
        unqualified = table.name
        schema_pattern = f"{table.schema}.*"
        
        for rule in self.limit_rules:
            if (rule.compiled_pattern.match(qualified) or
                rule.compiled_pattern.match(unqualified) or
                rule.compiled_pattern.match(schema_pattern)):
                return rule
        
        return None
    
    def _build_query(self, table: Table, limit_rule: Optional[LimitRule]) -> Tuple[str, List[Any]]:
        """Build sampling query for table.
        
        Args:
            table: Table to query
            limit_rule: Limit rule to apply
            
        Returns:
            Tuple of (query, parameters)
        """
        # Build column list - replace excluded columns with NULL
        excluded_cols = self._get_excluded_columns(table)
        column_exprs = []
        
        for col in table.columns:
            if col["name"] in excluded_cols:
                column_exprs.append("NULL")
            else:
                column_exprs.append(f'"{col["name"]}"')
        
        if not column_exprs:
            column_exprs = ["NULL"]
        
        col_list = ", ".join(column_exprs)
        
        query = f'SELECT {col_list} FROM "{table.schema}"."{table.name}"'
        params = []
        
        # Add WHERE clause for conditional limits
        if limit_rule and limit_rule.limit_type == LimitType.CONDITIONAL:
            query += f" WHERE {limit_rule.value}"
        
        # Add ORDER BY
        if self.ordered:
            if table.has_primary_key:
                pk_cols = ", ".join(f'"{col}"' for col in table.primary_key)
                order_dir = "DESC" if self.ordered_desc else "ASC"
                query += f" ORDER BY {pk_cols} {order_dir}"
            else:
                # Use ctid for ordering when no PK
                order_dir = "DESC" if self.ordered_desc else "ASC"
                query += f" ORDER BY ctid {order_dir}"
        elif self.random:
            query += " ORDER BY RANDOM()"
        
        # Add LIMIT
        if limit_rule:
            if limit_rule.limit_type == LimitType.NUMERIC:
                query += f" LIMIT %s"
                params.append(limit_rule.value)
            elif limit_rule.limit_type == LimitType.PERCENTAGE:
                # Get total count first
                count_query = f'SELECT COUNT(*) FROM "{table.schema}"."{table.name}"'
                # Note: percentage limits don't support WHERE clauses in the count
                
                with self.conn.cursor() as cur:
                    cur.execute(count_query, params)
                    total = cur.fetchone()[0]
                
                limit = max(1, int(total * limit_rule.value / 100))
                query += f" LIMIT %s"
                params.append(limit)
            # FULL and CONDITIONAL don't need LIMIT clause
        else:
            # Default limit
            query += " LIMIT 100"
            params.append(100)
        
        return query, params
    
    def _get_progress_bar(self, current: int, total: int, width: int = 20) -> str:
        """Generate a simple ASCII progress bar.
        
        Args:
            current: Current progress value
            total: Total value
            width: Width of progress bar in characters
            
        Returns:
            Progress bar string (e.g., "[=====>     ]")
        """
        if total == 0:
            return "[" + " " * width + "]"
        
        filled = int((current / total) * width)
        bar = "=" * filled + ">" * (1 if filled < width else 0) + " " * max(0, width - filled - 1)
        return f"[{bar}]"
    
    def _get_excluded_columns(self, table: Table) -> Set[str]:
        """Get set of excluded column names for table.
        
        Args:
            table: Table to check
            
        Returns:
            Set of excluded column names
        """
        excluded = set()
        qualified = f"{table.schema}.{table.name}"
        
        for pattern in self.exclude_columns:
            # Check if pattern matches table.column
            if "." in pattern:
                table_pattern, col_pattern = pattern.rsplit(".", 1)
                if self._match_pattern(qualified, table_pattern) or self._match_pattern(table.name, table_pattern):
                    if self._match_pattern("*", col_pattern) or col_pattern == "*":
                        # Exclude all columns
                        excluded.update(col["name"] for col in table.columns)
                    else:
                        # Match specific column
                        for col in table.columns:
                            if self._match_pattern(col["name"], col_pattern):
                                excluded.add(col["name"])
            else:
                # Column pattern only - check all tables
                for col in table.columns:
                    if self._match_pattern(col["name"], pattern):
                        excluded.add(col["name"])
        
        return excluded
    
    def _is_column_excluded(self, table: Table, column_name: str) -> bool:
        """Check if column is excluded.
        
        Args:
            table: Table containing column
            column_name: Column name to check
            
        Returns:
            True if column is excluded
        """
        return column_name in self._get_excluded_columns(table)
    
    def _match_pattern(self, text: str, pattern: str) -> bool:
        """Simple wildcard pattern matching."""
        import fnmatch
        return fnmatch.fnmatch(text, pattern)
    
    def verify_referential_integrity(self) -> Tuple[bool, List[Dict[str, Any]]]:
        """Verify referential integrity of sampled data.
        
        Checks that all foreign key values in sampled data exist in the
        referenced tables' sampled data.
        
        Returns:
            Tuple of (is_valid, violations_list)
            - is_valid: True if no violations found, False otherwise
            - violations_list: List of violation dictionaries with details
        """
        violations = []
        total_fks = sum(
            len(table.foreign_keys)
            for table_name, table in self.tables.items()
            if table_name in self.results
        )
        
        if self.verbose:
            self.logger.info(f"Verifying referential integrity for {total_fks} foreign key constraint(s)...")
        
        fk_count = 0
        
        # For each table with sampled data, check foreign key constraints
        for table_name, table in self.tables.items():
            if table_name not in self.results:
                continue
            
            if not self.results[table_name].rows:
                continue  # Skip empty tables
            
            for fk in table.foreign_keys:
                fk_count += 1
                ref_table = f"{fk.referenced_schema}.{fk.referenced_table}"
                
                # Skip if referenced table not in our tables
                if ref_table not in self.tables:
                    if self.verbose:
                        self.logger.debug(f"  [{fk_count}/{total_fks}] Skipping FK '{table_name}.{fk.name}': referenced table '{ref_table}' not in sample")
                    continue
                
                ref_table_obj = self.tables[ref_table]
                
                # Skip if referenced table has no primary key
                if not ref_table_obj.has_primary_key:
                    if self.verbose:
                        self.logger.debug(f"  [{fk_count}/{total_fks}] Skipping FK '{table_name}.{fk.name}': referenced table '{ref_table}' has no primary key")
                    continue
                
                # Skip if referenced table has no sampled data
                if ref_table not in self.results or not self.results[ref_table].rows:
                    if self.verbose:
                        self.logger.debug(f"  [{fk_count}/{total_fks}] Skipping FK '{table_name}.{fk.name}': referenced table '{ref_table}' has no sampled data")
                    continue
                
                # Get FK column indices in the source table
                fk_col_indices = [
                    i for i, col in enumerate(table.columns)
                    if col["name"] in fk.columns
                ]
                
                if not fk_col_indices:
                    continue  # Should not happen, but skip if FK columns not found
                
                # Get referenced PK column indices
                ref_pk_indices = [
                    i for i, col in enumerate(ref_table_obj.columns)
                    if col["name"] in fk.referenced_columns
                ]
                
                if not ref_pk_indices:
                    continue  # Should not happen, but skip if PK columns not found
                
                # Collect all FK values from sampled data
                fk_values = set()
                for row in self.results[table_name].rows:
                    fk_value = tuple(row[i] for i in fk_col_indices)
                    if None not in fk_value:  # Skip NULL foreign keys
                        fk_values.add(fk_value)
                
                if not fk_values:
                    if self.verbose:
                        self.logger.debug(f"  [{fk_count}/{total_fks}] FK '{table_name}.{fk.name}' -> '{ref_table}': no non-NULL FK values to check")
                    continue
                
                # Collect all PK values from referenced table's sampled data
                ref_pk_values = set()
                for row in self.results[ref_table].rows:
                    pk_value = tuple(row[i] for i in ref_pk_indices)
                    ref_pk_values.add(pk_value)
                
                # Find violations (FK values that don't exist in referenced table)
                missing_values = fk_values - ref_pk_values
                
                if missing_values:
                    violation = {
                        "constraint": fk.name,
                        "table": table_name,
                        "columns": fk.columns,
                        "referenced_table": ref_table,
                        "referenced_columns": fk.referenced_columns,
                        "violation_count": len(missing_values),
                        "sample_violations": list(missing_values)[:10],  # Show first 10
                    }
                    violations.append(violation)
                    
                    if self.verbose:
                        self.logger.warning(
                            f"  [{fk_count}/{total_fks}] ✗ FK '{table_name}.{fk.name}' -> '{ref_table}': "
                            f"{len(missing_values)} violation(s) found"
                        )
                else:
                    if self.verbose:
                        self.logger.info(
                            f"  [{fk_count}/{total_fks}] ✓ FK '{table_name}.{fk.name}' -> '{ref_table}': OK"
                        )
        
        is_valid = len(violations) == 0
        return is_valid, violations
    
    def _resolve_foreign_keys(self):
        """Resolve foreign key dependencies by including required rows."""
        fk_count = 0
        total_fks = sum(
            len(table.foreign_keys)
            for table_name, table in self.tables.items()
            if table_name in self.results
        )
        
        if self.verbose and total_fks > 0:
            self.logger.info(f"  Checking {total_fks} foreign key constraint(s)...")
        
        # For each table, check if referenced rows are included
        for table_name, table in self.tables.items():
            if table_name not in self.results:
                continue
            
            for fk in table.foreign_keys:
                fk_count += 1
                ref_table = f"{fk.referenced_schema}.{fk.referenced_table}"
                if ref_table not in self.tables:
                    continue
                
                ref_table_obj = self.tables[ref_table]
                if not ref_table_obj.has_primary_key:
                    if self.verbose:
                        self.logger.warning(
                            f"    [{fk_count}/{total_fks}] Foreign key '{table_name}.{fk.name}' references "
                            f"table '{ref_table}' which has no primary key. FK resolution will be skipped "
                            f"for this constraint."
                        )
                    continue
                
                if self.verbose:
                    self.logger.debug(f"    [{fk_count}/{total_fks}] Checking FK: {table_name} -> {ref_table}")
                
                # Get referenced values from current table
                ref_col_indices = [
                    i for i, col in enumerate(table.columns)
                    if col["name"] in fk.columns
                ]
                
                referenced_values = set()
                for row in self.results[table_name].rows:
                    ref_values = tuple(row[i] for i in ref_col_indices)
                    if None not in ref_values:  # Skip NULL foreign keys
                        referenced_values.add(ref_values)
                
                # Check which referenced rows are missing
                if ref_table in self.sampled_rows:
                    missing = referenced_values - self.sampled_rows[ref_table]
                else:
                    missing = referenced_values
                
                if missing:
                    # Fetch missing rows
                    if self.verbose:
                        self.logger.info(f"    [{fk_count}/{total_fks}] Adding {len(missing)} missing referenced row(s) from {ref_table} (FK: {table_name}.{fk.name})")
                    self._fetch_missing_rows(ref_table_obj, fk.referenced_columns, missing)
                elif self.verbose:
                    self.logger.debug(f"    [{fk_count}/{total_fks}] FK {table_name}.{fk.name} -> {ref_table}: all referenced rows present")
    
    def _fetch_missing_rows(
        self,
        table: Table,
        columns: List[str],
        values: Set[Tuple]
    ):
        """Fetch missing rows to satisfy foreign key constraints.
        
        Args:
            table: Table to fetch from
            columns: Column names to match
            values: Set of value tuples to fetch
        """
        if not values:
            return
        
        # Build query to fetch missing rows
        col_list = ", ".join(f'"{col}"' for col in [c["name"] for c in table.columns])
        placeholders = []
        params = []
        
        for value_tuple in values:
            if len(value_tuple) == 1:
                placeholders.append("(%s)")
                params.append(value_tuple[0])
            else:
                placeholders.append("(" + ", ".join(["%s"] * len(value_tuple)) + ")")
                params.extend(value_tuple)
        
        query = f'''
            SELECT {col_list}
            FROM "{table.schema}"."{table.name}"
            WHERE ({", ".join(f'"{col}"' for col in columns)}) IN ({", ".join(placeholders)})
        '''
        
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
        
        # Add to results
        if table.qualified_name not in self.results:
            self.results[table.qualified_name] = SamplingResult(
                table_schema=table.schema,
                table_name=table.name,
                rows=[],
                row_count=0,
            )
        
        # Avoid duplicates
        existing_pks = set()
        if table.has_primary_key:
            pk_indices = [i for i, col in enumerate(table.columns) if col["name"] in table.primary_key]
            existing_pks = {
                tuple(row[i] for i in pk_indices)
                for row in self.results[table.qualified_name].rows
            }
        
        new_rows = []
        for row in rows:
            if table.has_primary_key:
                pk_values = tuple(row[i] for i in pk_indices)
                if pk_values not in existing_pks:
                    new_rows.append(row)
                    existing_pks.add(pk_values)
            else:
                new_rows.append(row)
        
        self.results[table.qualified_name].rows.extend(new_rows)
        self.results[table.qualified_name].row_count += len(new_rows)
        
        # Update sampled_rows
        if table.has_primary_key:
            pk_indices = [i for i, col in enumerate(table.columns) if col["name"] in table.primary_key]
            if table.qualified_name not in self.sampled_rows:
                self.sampled_rows[table.qualified_name] = set()
            self.sampled_rows[table.qualified_name].update(
                tuple(row[i] for i in pk_indices)
                for row in new_rows
            )


def parse_limit_rules(limit_specs: List[str]) -> List[LimitRule]:
    """Parse limit rule specifications.
    
    Args:
        limit_specs: List of limit specifications (e.g., ["users=1000", "*=100"])
        
    Returns:
        List of LimitRule objects
    """
    rules = []
    
    for spec in limit_specs:
        # Handle comma-separated rules
        for rule_str in spec.split(","):
            rule_str = rule_str.strip()
            if "=" not in rule_str:
                continue
            
            pattern, value = rule_str.split("=", 1)
            pattern = pattern.strip()
            value = value.strip()
            
            # Compile pattern to regex
            regex_pattern = "^" + re.escape(pattern).replace("\\*", ".*") + "$"
            compiled = re.compile(regex_pattern, re.IGNORECASE)
            
            # Determine limit type
            if value == "*":
                limit_type = LimitType.FULL
                limit_value = None
            elif value.endswith("%"):
                limit_type = LimitType.PERCENTAGE
                limit_value = float(value[:-1])
            elif value.upper().startswith("WHERE") or " " in value:
                limit_type = LimitType.CONDITIONAL
                limit_value = value
            else:
                try:
                    limit_type = LimitType.NUMERIC
                    limit_value = int(value)
                except ValueError:
                    # Treat as conditional
                    limit_type = LimitType.CONDITIONAL
                    limit_value = value
            
            rules.append(LimitRule(
                pattern=pattern,
                limit_type=limit_type,
                value=limit_value,
                compiled_pattern=compiled,
            ))
    
    return rules

