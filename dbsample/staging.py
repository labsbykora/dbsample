"""Staging schema management for sampled data."""

from typing import Optional, List, Dict
import psycopg
from dbsample.logger import Logger


class StagingManager:
    """Manages temporary staging schema for sampled data."""
    
    def __init__(
        self,
        conn: psycopg.Connection,
        schema_name: str = "_dbsample",
        logger: Optional[Logger] = None,
    ):
        """Initialize staging manager.
        
        Args:
            conn: Database connection
            schema_name: Name of staging schema
            logger: Logger instance
        """
        self.conn = conn
        self.schema_name = schema_name
        self.logger = logger or Logger()
        self._schema_created = False
    
    def create_schema(self, force: bool = False) -> bool:
        """Create staging schema.
        
        Args:
            force: If True, drop existing schema first
            
        Returns:
            True if schema was created, False otherwise
        """
        try:
            # Rollback any aborted transaction first
            try:
                self.conn.rollback()
            except Exception:
                pass  # Ignore rollback errors
            
            with self.conn.cursor() as cur:
                # Check if schema exists
                cur.execute("""
                    SELECT EXISTS(
                        SELECT 1 FROM pg_namespace WHERE nspname = %s
                    )
                """, [self.schema_name])
                exists = cur.fetchone()[0]
                
                if exists:
                    if force:
                        self.logger.info(f"Dropping existing staging schema: {self.schema_name}")
                        cur.execute(f'DROP SCHEMA IF EXISTS "{self.schema_name}" CASCADE')
                        self.conn.commit()
                    else:
                        self.logger.warning(
                            f"Staging schema {self.schema_name} already exists. "
                            f"Use --force to drop it, or --keep to preserve it."
                        )
                        return False
                
                # Create schema
                self.logger.info(f"Creating staging schema: {self.schema_name}")
                cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{self.schema_name}"')
                self.conn.commit()
                self._schema_created = True
                return True
                
        except psycopg.errors.InsufficientPrivilege as e:
            # Rollback on error
            try:
                self.conn.rollback()
            except Exception:
                pass
            self.logger.error(
                f"Insufficient privileges to create staging schema: {e}. "
                f"Falling back to direct query mode."
            )
            return False
        except Exception as e:
            # Rollback on error
            try:
                self.conn.rollback()
            except Exception:
                pass
            self.logger.error(f"Failed to create staging schema: {e}")
            return False
    
    def drop_schema(self):
        """Drop staging schema."""
        if not self._schema_created:
            return
        
        try:
            # Rollback any aborted transaction first
            try:
                self.conn.rollback()
            except Exception:
                pass  # Ignore rollback errors
            
            with self.conn.cursor() as cur:
                self.logger.info(f"Dropping staging schema: {self.schema_name}")
                cur.execute(f'DROP SCHEMA IF EXISTS "{self.schema_name}" CASCADE')
                self.conn.commit()
                self._schema_created = False
        except Exception as e:
            self.logger.warning(f"Failed to drop staging schema: {e}")
            # Try to rollback again in case of error
            try:
                self.conn.rollback()
            except Exception:
                pass
    
    def create_staging_table(
        self,
        source_schema: str,
        source_table: str,
        columns: List[Dict[str, any]],
    ) -> str:
        """Create a staging table with same structure as source table.
        
        Args:
            source_schema: Source table schema
            source_table: Source table name
            columns: List of column definitions
            
        Returns:
            Qualified staging table name
        """
        staging_table = f"{self.schema_name}.{source_table}"
        
        # Build column definitions
        col_defs = []
        for col in columns:
            col_def = f'"{col["name"]}" {col["type"]}'
            if col.get("not_null"):
                col_def += " NOT NULL"
            col_defs.append(col_def)
        
        # Create table
        try:
            # Rollback any aborted transaction first
            try:
                self.conn.rollback()
            except Exception:
                pass  # Ignore rollback errors
            
            with self.conn.cursor() as cur:
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS "{self.schema_name}"."{source_table}" (
                        {', '.join(col_defs)}
                    )
                """)
                self.conn.commit()
        except Exception as e:
            # Rollback on error
            try:
                self.conn.rollback()
            except Exception:
                pass
            raise
        
        return staging_table
    
    def copy_data_to_staging(
        self,
        source_schema: str,
        source_table: str,
        staging_table: str,
        query: str,
        params: List[any],
    ) -> int:
        """Copy sampled data to staging table.
        
        Args:
            source_schema: Source table schema
            source_table: Source table name
            staging_table: Staging table name (schema.table format)
            query: SELECT query to get data
            params: Query parameters
            
        Returns:
            Number of rows copied
        """
        try:
            # Rollback any aborted transaction first
            try:
                self.conn.rollback()
            except Exception:
                pass  # Ignore rollback errors
            
            with self.conn.cursor() as cur:
                # Use INSERT INTO ... SELECT for better performance
                # Properly quote schema and table separately
                # staging_table is in format "schema.table", extract table name
                if '.' in staging_table:
                    # Extract just the table name (after the dot)
                    table_name = staging_table.split('.', 1)[1]
                else:
                    table_name = staging_table
                insert_query = f'INSERT INTO "{self.schema_name}"."{table_name}" {query}'
                cur.execute(insert_query, params)
                row_count = cur.rowcount
                self.conn.commit()
                return row_count
        except Exception as e:
            # Rollback on error
            try:
                self.conn.rollback()
            except Exception:
                pass
            raise
    
    def create_staging_indexes(
        self,
        table_name: str,
        indexes: List[Dict[str, any]],
    ):
        """Create indexes on staging table.
        
        Args:
            table_name: Staging table name
            indexes: List of index definitions
        """
        for idx in indexes:
            try:
                # Rollback any aborted transaction first
                try:
                    self.conn.rollback()
                except Exception:
                    pass  # Ignore rollback errors
                
                with self.conn.cursor() as cur:
                    # Extract index definition and adapt for staging table
                    idx_def = idx["definition"]
                    # Replace table name with staging table name
                    idx_def = idx_def.replace(
                        f'"{idx.get("table_schema", "")}"."{idx.get("table_name", "")}"',
                        f'"{self.schema_name}"."{table_name}"'
                    )
                    cur.execute(idx_def)
                    self.conn.commit()
            except Exception as e:
                # Rollback on error
                try:
                    self.conn.rollback()
                except Exception:
                    pass
                self.logger.debug(f"Could not create index {idx.get('name')}: {e}")
    
    def get_staging_data(
        self,
        table_name: str,
        columns: List[str],
    ) -> List[tuple]:
        """Get data from staging table.
        
        Args:
            table_name: Staging table name
            columns: List of column names
            
        Returns:
            List of row tuples
        """
        try:
            # Rollback any aborted transaction first
            try:
                self.conn.rollback()
            except Exception:
                pass  # Ignore rollback errors
            
            col_list = ", ".join(f'"{col}"' for col in columns)
            with self.conn.cursor() as cur:
                cur.execute(f'SELECT {col_list} FROM "{self.schema_name}"."{table_name}"')
                return cur.fetchall()
        except Exception as e:
            # Rollback on error
            try:
                self.conn.rollback()
            except Exception:
                pass
            raise
    
    def verify_foreign_keys(
        self,
        tables: List[any],
        resolver: any,
    ) -> Dict[str, List[str]]:
        """Verify foreign key constraints in staging schema.
        
        Args:
            tables: List of Table objects
            resolver: DependencyResolver instance
            
        Returns:
            Dictionary mapping table names to list of FK violations
        """
        violations = {}
        
        for table in tables:
            table_name = table.name
            for fk in table.foreign_keys:
                ref_table = fk.referenced_table
                
                # Check if referenced rows exist
                with self.conn.cursor() as cur:
                    cols = ", ".join(f'"{col}"' for col in fk.columns)
                    ref_cols = ", ".join(f'"{col}"' for col in fk.referenced_columns)
                    
                    cur.execute(f"""
                        SELECT COUNT(*)
                        FROM "{self.schema_name}"."{table_name}" t
                        WHERE EXISTS (
                            SELECT 1
                            FROM "{self.schema_name}"."{ref_table}" r
                            WHERE ({cols}) = ({ref_cols})
                        )
                    """)
                    # This is a simplified check - full validation would be more complex
                    
        return violations
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup if needed."""
        # Don't auto-cleanup here - let caller decide with --keep flag
        pass

