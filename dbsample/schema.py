"""Schema discovery and database object enumeration."""

from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import psycopg


class TableType(Enum):
    """Table type enumeration."""
    ORDINARY = "r"
    PARTITIONED = "p"
    FOREIGN = "f"
    TEMPORARY = "t"


@dataclass
class ForeignKey:
    """Foreign key constraint information."""
    name: str
    table_schema: str
    table_name: str
    constraint_name: str
    columns: List[str]
    referenced_schema: str
    referenced_table: str
    referenced_columns: List[str]
    on_delete: str
    on_update: str


@dataclass
class Table:
    """Table metadata."""
    schema: str
    name: str
    table_type: TableType
    is_partitioned: bool
    parent_table: Optional[Tuple[str, str]] = None  # (schema, name)
    columns: List[Dict[str, any]] = None
    primary_key: Optional[List[str]] = None
    foreign_keys: List[ForeignKey] = None
    unique_constraints: List[Dict[str, any]] = None
    check_constraints: List[Dict[str, any]] = None
    indexes: List[Dict[str, any]] = None
    triggers: List[Dict[str, any]] = None
    
    def __post_init__(self):
        if self.columns is None:
            self.columns = []
        if self.foreign_keys is None:
            self.foreign_keys = []
        if self.unique_constraints is None:
            self.unique_constraints = []
        if self.check_constraints is None:
            self.check_constraints = []
        if self.indexes is None:
            self.indexes = []
    
    @property
    def qualified_name(self) -> str:
        """Get qualified table name."""
        return f"{self.schema}.{self.name}"
    
    @property
    def has_primary_key(self) -> bool:
        """Check if table has primary key."""
        return self.primary_key is not None and len(self.primary_key) > 0


class SchemaDiscovery:
    """Discover database schema and objects."""
    
    def __init__(self, conn: psycopg.Connection):
        """Initialize schema discovery.
        
        Args:
            conn: Database connection
        """
        self.conn = conn
    
    def get_tables(
        self,
        schemas: Optional[List[str]] = None,
        exclude_schemas: Optional[List[str]] = None,
        exclude_tables: Optional[List[str]] = None,
    ) -> List[Table]:
        """Get all tables in database.
        
        Args:
            schemas: List of schemas to include (None = all)
            exclude_schemas: List of schemas to exclude
            exclude_tables: List of table patterns to exclude
            
        Returns:
            List of Table objects
        """
        if exclude_schemas is None:
            exclude_schemas = ["pg_catalog", "information_schema", "pg_toast"]
        
        with self.conn.cursor() as cur:
            # Build schema filter and parameters
            schema_filter = "TRUE"
            params = []
            
            if schemas:
                schema_placeholders = ",".join(["%s"] * len(schemas))
                schema_filter = f"n.nspname IN ({schema_placeholders})"
                params.extend(schemas)
            elif exclude_schemas:
                exclude_placeholders = ",".join(["%s"] * len(exclude_schemas))
                schema_filter = f"n.nspname NOT IN ({exclude_placeholders})"
                params.extend(exclude_schemas)
            
            # Build query with proper parameterization
            query = """
                SELECT 
                    n.nspname AS schema_name,
                    c.relname AS table_name,
                    c.relkind AS table_type,
                    c.relispartition AS is_partition,
                    pg_get_expr(c.relpartbound, c.oid) AS partition_bound
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE c.relkind IN ('r', 'p', 'f')
                    AND """ + schema_filter + """
                    AND NOT (n.nspname = 'pg_catalog' AND c.relname LIKE 'pg_%%')
                ORDER BY n.nspname, c.relname
            """
            
            cur.execute(query, params)
            tables = []
            
            for row in cur.fetchall():
                schema_name, table_name, relkind, is_partition, partition_bound = row
                
                # Check if table should be excluded
                if self._should_exclude_table(schema_name, table_name, exclude_tables):
                    continue
                
                table_type = TableType(relkind)
                
                # Skip foreign tables and temporary tables
                if table_type == TableType.FOREIGN:
                    continue
                if table_type == TableType.TEMPORARY:
                    continue
                
                table = Table(
                    schema=schema_name,
                    name=table_name,
                    table_type=table_type,
                    is_partitioned=is_partition or (table_type == TableType.PARTITIONED),
                )
                
                # Get table details
                self._enrich_table(table)
                tables.append(table)
            
            return tables
    
    def _should_exclude_table(
        self,
        schema: str,
        table: str,
        exclude_patterns: Optional[List[str]]
    ) -> bool:
        """Check if table matches exclusion patterns."""
        if not exclude_patterns:
            return False
        
        qualified = f"{schema}.{table}"
        unqualified = table
        
        for pattern in exclude_patterns:
            if self._match_pattern(qualified, pattern) or self._match_pattern(unqualified, pattern):
                return True
        
        return False
    
    def _match_pattern(self, text: str, pattern: str) -> bool:
        """Simple wildcard pattern matching."""
        import fnmatch
        return fnmatch.fnmatch(text, pattern)
    
    def _enrich_table(self, table: Table):
        """Enrich table with columns, constraints, etc."""
        with self.conn.cursor() as cur:
            # Get columns (including IDENTITY column information for PostgreSQL 10+)
            cur.execute("""
                SELECT 
                    a.attname AS column_name,
                    pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
                    a.attnotnull AS not_null,
                    pg_get_expr(ad.adbin, ad.adrelid) AS default_value,
                    a.attnum AS column_number,
                    a.attidentity AS identity_type
                FROM pg_attribute a
                LEFT JOIN pg_attrdef ad ON a.attrelid = ad.adrelid AND a.attnum = ad.adnum
                WHERE a.attrelid = %s::regclass
                    AND a.attnum > 0
                    AND NOT a.attisdropped
                ORDER BY a.attnum
            """, [table.qualified_name])
            
            table.columns = []
            for row in cur.fetchall():
                col_data = {
                    "name": row[0],
                    "type": row[1],
                    "not_null": row[2],
                    "default": row[3],
                    "number": row[4],
                }
                # Add IDENTITY column information (PostgreSQL 10+)
                # attidentity: 'a' = ALWAYS, 'd' = BY DEFAULT, '' = not IDENTITY
                if row[5] and row[5] in ('a', 'd'):
                    col_data["identity"] = row[5]
                    # Get sequence name for IDENTITY column
                    try:
                        cur.execute("""
                            SELECT pg_get_serial_sequence(%s, %s)
                        """, [table.qualified_name, row[0]])
                        seq_result = cur.fetchone()
                        if seq_result and seq_result[0]:
                            # Extract schema and sequence name from full sequence name
                            seq_full_name = seq_result[0]
                            if '.' in seq_full_name:
                                seq_schema, seq_name = seq_full_name.rsplit('.', 1)
                                col_data["identity_sequence"] = {
                                    "schema": seq_schema.strip('"'),
                                    "name": seq_name.strip('"'),
                                    "full_name": seq_full_name
                                }
                    except Exception:
                        # If pg_get_serial_sequence fails, skip IDENTITY sequence info
                        # This can happen if the column isn't actually IDENTITY or on older PostgreSQL
                        pass
                
                table.columns.append(col_data)
            
            # Get primary key
            cur.execute("""
                SELECT a.attname
                FROM pg_index i
                JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
                WHERE i.indrelid = %s::regclass
                    AND i.indisprimary
                ORDER BY array_position(i.indkey, a.attnum)
            """, [table.qualified_name])
            
            pk_cols = [row[0] for row in cur.fetchall()]
            if pk_cols:
                table.primary_key = pk_cols
            
            # Get foreign keys
            cur.execute("""
                SELECT
                    tc.constraint_name,
                    kcu.column_name,
                    ccu.table_schema AS foreign_table_schema,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name,
                    rc.delete_rule,
                    rc.update_rule
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
                JOIN information_schema.referential_constraints AS rc
                    ON rc.constraint_name = tc.constraint_name
                    AND rc.constraint_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND tc.table_schema = %s
                    AND tc.table_name = %s
                ORDER BY tc.constraint_name, kcu.ordinal_position
            """, [table.schema, table.name])
            
            fk_dict: Dict[str, ForeignKey] = {}
            for row in cur.fetchall():
                constraint_name, col, ref_schema, ref_table, ref_col, del_rule, upd_rule = row
                
                if constraint_name not in fk_dict:
                    fk_dict[constraint_name] = ForeignKey(
                        name=constraint_name,
                        table_schema=table.schema,
                        table_name=table.name,
                        constraint_name=constraint_name,
                        columns=[],
                        referenced_schema=ref_schema,
                        referenced_table=ref_table,
                        referenced_columns=[],
                        on_delete=del_rule,
                        on_update=upd_rule,
                    )
                
                fk_dict[constraint_name].columns.append(col)
                fk_dict[constraint_name].referenced_columns.append(ref_col)
            
            table.foreign_keys = list(fk_dict.values())
            
            # Get unique constraints
            cur.execute("""
                SELECT
                    tc.constraint_name,
                    kcu.column_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                WHERE tc.constraint_type = 'UNIQUE'
                    AND tc.table_schema = %s
                    AND tc.table_name = %s
                ORDER BY tc.constraint_name, kcu.ordinal_position
            """, [table.schema, table.name])
            
            unique_dict: Dict[str, List[str]] = {}
            for row in cur.fetchall():
                constraint_name, col = row
                if constraint_name not in unique_dict:
                    unique_dict[constraint_name] = []
                unique_dict[constraint_name].append(col)
            
            table.unique_constraints = [
                {"name": name, "columns": cols}
                for name, cols in unique_dict.items()
            ]
            
            # Get check constraints
            cur.execute("""
                SELECT
                    conname AS constraint_name,
                    pg_get_constraintdef(oid) AS constraint_definition
                FROM pg_constraint
                WHERE conrelid = %s::regclass
                    AND contype = 'c'
            """, [table.qualified_name])
            
            table.check_constraints = [
                {"name": row[0], "definition": row[1]}
                for row in cur.fetchall()
            ]
            
            # Get indexes
            cur.execute("""
                SELECT
                    i.relname AS index_name,
                    pg_get_indexdef(i.oid) AS index_definition
                FROM pg_index idx
                JOIN pg_class i ON i.oid = idx.indexrelid
                WHERE idx.indrelid = %s::regclass
                    AND NOT idx.indisprimary
            """, [table.qualified_name])
            
            table.indexes = [
                {"name": row[0], "definition": row[1]}
                for row in cur.fetchall()
            ]
            
            # Get triggers
            cur.execute("""
                SELECT
                    trigger_name,
                    event_manipulation,
                    action_statement,
                    action_timing
                FROM information_schema.triggers
                WHERE event_object_schema = %s
                    AND event_object_table = %s
            """, [table.schema, table.name])
            
            table.triggers = [
                {
                    "name": row[0],
                    "event": row[1],
                    "statement": row[2],
                    "timing": row[3],
                }
                for row in cur.fetchall()
            ]
    
    def get_database_objects(
        self,
        schemas: Optional[List[str]] = None,
        exclude_schemas: Optional[List[str]] = None,
    ) -> Dict[str, List[Dict[str, any]]]:
        """Get additional database objects (types, views, functions, sequences).
        
        Returns:
            Dictionary with keys: types, views, materialized_views, functions, sequences, extensions
        """
        objects = {
            "types": [],
            "views": [],
            "materialized_views": [],
            "functions": [],
            "sequences": [],
            "extensions": [],
        }
        
        if exclude_schemas is None:
            exclude_schemas = ["pg_catalog", "information_schema", "pg_toast"]
        
        with self.conn.cursor() as cur:
            # Get custom types
            schema_filter = "TRUE"
            params = []
            if schemas:
                schema_placeholders = ",".join(["%s"] * len(schemas))
                schema_filter = f"n.nspname IN ({schema_placeholders})"
                params.extend(schemas)
            elif exclude_schemas:
                exclude_placeholders = ",".join(["%s"] * len(exclude_schemas))
                schema_filter = f"n.nspname NOT IN ({exclude_placeholders})"
                params.extend(exclude_schemas)
            
            cur.execute("""
                SELECT n.nspname, t.typname, pg_catalog.format_type(t.oid, NULL)
                FROM pg_type t
                JOIN pg_namespace n ON n.oid = t.typnamespace
                LEFT JOIN pg_class c ON c.oid = t.typrelid AND t.typtype = 'c'
                WHERE t.typtype IN ('c', 'd', 'e')
                    AND (t.typtype != 'c' OR c.relkind IS NULL OR c.relkind != 'r')
                    AND """ + schema_filter, params)
            
            objects["types"] = [
                {"schema": row[0], "name": row[1], "definition": row[2]}
                for row in cur.fetchall()
            ]
            
            # Get views
            cur.execute("""
                SELECT n.nspname, c.relname, pg_get_viewdef(c.oid, true)
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE c.relkind = 'v'
                    AND """ + schema_filter, params)
            
            objects["views"] = [
                {"schema": row[0], "name": row[1], "definition": row[2]}
                for row in cur.fetchall()
            ]
            
            # Get materialized views
            cur.execute("""
                SELECT n.nspname, c.relname, pg_get_viewdef(c.oid, true)
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE c.relkind = 'm'
                    AND """ + schema_filter, params)
            
            objects["materialized_views"] = [
                {"schema": row[0], "name": row[1], "definition": row[2]}
                for row in cur.fetchall()
            ]
            
            # Get sequences
            cur.execute("""
                SELECT n.nspname, c.relname
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE c.relkind = 'S'
                    AND """ + schema_filter, params)
            
            objects["sequences"] = [
                {"schema": row[0], "name": row[1]}
                for row in cur.fetchall()
            ]
            
            # Get extensions
            cur.execute("""
                SELECT extname, extversion
                FROM pg_extension
            """)
            
            objects["extensions"] = [
                {"name": row[0], "version": row[1]}
                for row in cur.fetchall()
            ]
        
        return objects

