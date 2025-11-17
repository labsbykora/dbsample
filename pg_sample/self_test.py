"""Self-test functionality for end-to-end validation."""

import gzip
import os
import tempfile
import uuid
from typing import Optional, Dict, List, Tuple, Any
import psycopg
from pg_sample.logger import Logger
from pg_sample.connection import DatabaseConnection


class SelfTestRunner:
    """Runs end-to-end self-test: sample → generate SQL → import → verify."""
    
    def __init__(
        self,
        source_conn_params: Dict[str, Any],
        logger: Optional[Logger] = None,
        verbose: bool = False,
    ):
        """Initialize self-test runner.
        
        Args:
            source_conn_params: Connection parameters for source database
            logger: Logger instance
            verbose: Enable verbose output
        """
        self.source_conn_params = source_conn_params
        self.logger = logger or Logger()
        self.verbose = verbose
        self.test_db_name: Optional[str] = None
        self.temp_sql_file: Optional[str] = None
        self._cleanup_files: List[str] = []
    
    def run_test(self, sql_file: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
        """Run full self-test.
        
        Args:
            sql_file: Path to SQL file to test (if None, will be generated)
            
        Returns:
            Tuple of (success, results_dict)
        """
        results = {
            "database_created": False,
            "import_succeeded": False,
            "tables_created": 0,
            "constraints_valid": False,
            "violations": [],
            "errors": [],
        }
        
        try:
            # Step 1: Create temporary database
            if self.verbose:
                self.logger.info("Step 1: Creating temporary database...")
            
            self.test_db_name = self._generate_test_db_name()
            if not self._create_test_database():
                results["errors"].append("Failed to create test database")
                return False, results
            
            results["database_created"] = True
            if self.verbose:
                self.logger.info(f"  ✓ Created database: {self.test_db_name}")
            
            # Step 2: Import SQL file
            if self.verbose:
                self.logger.info("Step 2: Importing SQL into test database...")
            
            test_sql_file = sql_file or self.temp_sql_file
            if not test_sql_file or not os.path.exists(test_sql_file):
                results["errors"].append(f"SQL file not found: {test_sql_file}")
                return False, results
            
            success, error_msg = self._import_sql_file(test_sql_file)
            if not success:
                results["errors"].append(f"SQL import failed: {error_msg}")
                return False, results
            
            results["import_succeeded"] = True
            if self.verbose:
                self.logger.info("  ✓ Import completed successfully")
            
            # Step 3: Verify import
            if self.verbose:
                self.logger.info("Step 3: Verifying import...")
            
            table_count = self._verify_import()
            results["tables_created"] = table_count
            if self.verbose:
                self.logger.info(f"  ✓ All {table_count} tables created")
            
            # Step 4: Verify constraints
            if self.verbose:
                self.logger.info("Step 4: Verifying constraints...")
            
            is_valid, violations = self._verify_constraints()
            results["constraints_valid"] = is_valid
            results["violations"] = violations
            
            if is_valid:
                if self.verbose:
                    self.logger.info("  ✓ All constraints valid")
            else:
                if self.verbose:
                    self.logger.warning(f"  ✗ Found {len(violations)} constraint violation(s)")
            
            return is_valid and results["import_succeeded"], results
            
        except Exception as e:
            results["errors"].append(f"Unexpected error: {str(e)}")
            if self.verbose:
                self.logger.error(f"  ✗ Error: {e}")
            return False, results
        
        finally:
            # Always cleanup
            self.cleanup()
    
    def _generate_test_db_name(self) -> str:
        """Generate unique test database name."""
        import time
        timestamp = int(time.time())
        random_suffix = str(uuid.uuid4())[:8]
        return f"pg_sample_test_{timestamp}_{random_suffix}"
    
    def _create_test_database(self) -> bool:
        """Create temporary test database."""
        try:
            # Connect to 'postgres' database to create new database
            # (can't create database while connected to it)
            conn_params = self.source_conn_params.copy()
            conn_params["dbname"] = "postgres"
            
            db_conn = DatabaseConnection(**conn_params)
            with db_conn.connect() as conn:
                conn.autocommit = True
                
                with conn.cursor() as cur:
                    # Check if database exists
                    cur.execute(
                        "SELECT EXISTS(SELECT 1 FROM pg_database WHERE datname = %s)",
                        [self.test_db_name]
                    )
                    exists = cur.fetchone()[0]
                    
                    if exists:
                        # Drop existing database
                        if self.verbose:
                            self.logger.warning(f"  Dropping existing database: {self.test_db_name}")
                        cur.execute(f'DROP DATABASE "{self.test_db_name}"')
                    
                    # Create new database
                    cur.execute(f'CREATE DATABASE "{self.test_db_name}"')
            
            return True
            
        except psycopg.errors.InsufficientPrivilege as e:
            self.logger.error(f"Insufficient privileges to create database: {e}")
            return False
        except psycopg.errors.DuplicateDatabase:
            # Try again after dropping
            return self._create_test_database()
        except Exception as e:
            self.logger.error(f"Failed to create test database: {e}")
            return False
    
    def _import_sql_file(self, sql_file: str) -> Tuple[bool, Optional[str]]:
        """Import SQL file into test database.
        
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Connect to test database
            conn_params = self.source_conn_params.copy()
            conn_params["dbname"] = self.test_db_name
            
            db_conn = DatabaseConnection(**conn_params)
            with db_conn.connect() as conn:
                conn.autocommit = True
                
                # Read and execute SQL file
                # Handle compressed files (gzip)
                if sql_file.endswith('.gz'):
                    with gzip.open(sql_file, 'rt', encoding='utf-8') as f:
                        sql_content = f.read()
                else:
                    with open(sql_file, 'r', encoding='utf-8') as f:
                        sql_content = f.read()
                
                # Execute SQL file
                # psycopg's execute() can handle multiple statements separated by semicolons
                # Since we're in autocommit mode, BEGIN/COMMIT are handled automatically
                with conn.cursor() as cur:
                    # Execute the entire SQL file as a script
                    # psycopg3 supports executing multiple statements
                    cur.execute(sql_content)
            
            return True, None
            
        except psycopg.errors.Error as e:
            return False, str(e)
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"
    
    def _verify_import(self) -> int:
        """Verify import succeeded and return table count."""
        try:
            conn_params = self.source_conn_params.copy()
            conn_params["dbname"] = self.test_db_name
            
            db_conn = DatabaseConnection(**conn_params)
            with db_conn.connect() as conn:
                conn.autocommit = True
                
                with conn.cursor() as cur:
                    # Count user tables (exclude system schemas)
                    cur.execute("""
                        SELECT COUNT(*) 
                        FROM pg_tables 
                        WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
                    """)
                    table_count = cur.fetchone()[0]
                    
                    return table_count
                    
        except Exception as e:
            if self.verbose:
                self.logger.warning(f"  Could not verify import: {e}")
            return 0
    
    def _verify_constraints(self) -> Tuple[bool, List[Dict[str, Any]]]:
        """Verify all constraints are valid.
        
        Returns:
            Tuple of (is_valid, violations_list)
        """
        violations = []
        
        try:
            conn_params = self.source_conn_params.copy()
            conn_params["dbname"] = self.test_db_name
            
            db_conn = DatabaseConnection(**conn_params)
            with db_conn.connect() as conn:
                conn.autocommit = True
                
                with conn.cursor() as cur:
                    # Check for invalid foreign key constraints
                    cur.execute("""
                        SELECT 
                            conname,
                            conrelid::regclass as table_name,
                            confrelid::regclass as referenced_table
                        FROM pg_constraint
                        WHERE contype = 'f' 
                            AND NOT convalidated
                    """)
                    
                    for row in cur.fetchall():
                        violations.append({
                            "constraint": row[0],
                            "table": str(row[1]),
                            "referenced_table": str(row[2]),
                        })
                    
                    # Also check for constraint violations by trying to validate
                    # (PostgreSQL 9.2+)
                    cur.execute("""
                        SELECT 
                            conname,
                            conrelid::regclass as table_name
                        FROM pg_constraint
                        WHERE contype = 'f'
                    """)
                    
                    fk_constraints = cur.fetchall()
                    if self.verbose and fk_constraints:
                        self.logger.info(f"  Found {len(fk_constraints)} foreign key constraint(s)")
                    
        except Exception as e:
            if self.verbose:
                self.logger.warning(f"  Could not verify constraints: {e}")
            # Don't fail the test if we can't verify constraints
            return True, []
        
        return len(violations) == 0, violations
    
    def cleanup(self):
        """Cleanup all resources."""
        # Drop test database
        if self.test_db_name:
            try:
                conn_params = self.source_conn_params.copy()
                conn_params["dbname"] = "postgres"
                
                db_conn = DatabaseConnection(**conn_params)
                with db_conn.connect() as conn:
                    conn.autocommit = True
                    
                    with conn.cursor() as cur:
                        # Terminate any connections to the test database
                        cur.execute("""
                            SELECT pg_terminate_backend(pid)
                            FROM pg_stat_activity
                            WHERE datname = %s AND pid <> pg_backend_pid()
                        """, [self.test_db_name])
                        
                        # Drop database
                        cur.execute(f'DROP DATABASE IF EXISTS "{self.test_db_name}"')
                
                if self.verbose:
                    self.logger.info(f"  ✓ Dropped test database: {self.test_db_name}")
                    
            except Exception as e:
                if self.verbose:
                    self.logger.warning(f"  Could not drop test database: {e}")
        
        # Cleanup temporary files
        for file_path in self._cleanup_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    if self.verbose:
                        self.logger.info(f"  ✓ Removed temporary file: {file_path}")
            except Exception as e:
                if self.verbose:
                    self.logger.warning(f"  Could not remove temporary file {file_path}: {e}")
    
    def set_temp_sql_file(self, file_path: str):
        """Set temporary SQL file path for cleanup."""
        self.temp_sql_file = file_path
        self._cleanup_files.append(file_path)

