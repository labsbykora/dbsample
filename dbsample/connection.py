"""Database connection handling with authentication and SSL support."""

import os
import sys
from typing import Optional, Dict, Any
from urllib.parse import urlparse, parse_qs
import psycopg
from psycopg.conninfo import conninfo_to_dict


class DatabaseConnection:
    """Manages PostgreSQL database connections with authentication and SSL."""
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        dbname: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        connection_uri: Optional[str] = None,
        ssl_mode: str = "prefer",
        ssl_cert: Optional[str] = None,
        ssl_key: Optional[str] = None,
        ssl_ca: Optional[str] = None,
    ):
        """Initialize database connection parameters.
        
        Args:
            host: Database host address
            port: Database port number
            dbname: Database name
            username: Connection username
            password: Connection password
            connection_uri: PostgreSQL connection URI
            ssl_mode: SSL mode (disable, allow, prefer, require, verify-ca, verify-full)
            ssl_cert: Client SSL certificate file path
            ssl_key: Client SSL key file path
            ssl_ca: SSL CA certificate file path
        """
        self.host = host or os.getenv("PGHOST")
        self.port = port or int(os.getenv("PGPORT", "5432"))
        self.dbname = dbname or os.getenv("PGDATABASE") or os.getenv("USER")
        self.username = username or os.getenv("PGUSER")
        self.password = password
        self.connection_uri = connection_uri
        self.ssl_mode = ssl_mode
        self.ssl_cert = ssl_cert
        self.ssl_key = ssl_key
        self.ssl_ca = ssl_ca
        self._conn: Optional[psycopg.Connection] = None
        
    def _build_connection_params(self) -> Dict[str, Any]:
        """Build connection parameters dictionary."""
        params: Dict[str, Any] = {}
        
        if self.connection_uri:
            # Parse connection URI
            parsed = urlparse(self.connection_uri)
            if parsed.scheme not in ("postgresql", "postgres"):
                raise ValueError(f"Invalid connection URI scheme: {parsed.scheme}")
            
            params["host"] = parsed.hostname or self.host
            params["port"] = parsed.port or self.port
            params["dbname"] = parsed.path.lstrip("/") if parsed.path else self.dbname
            params["user"] = parsed.username or self.username
            if parsed.password:
                params["password"] = parsed.password
            elif self.password:
                params["password"] = self.password
            elif os.getenv("PGPASSWORD"):
                params["password"] = os.getenv("PGPASSWORD")
            
            # Parse query parameters
            if parsed.query:
                query_params = parse_qs(parsed.query)
                for key, values in query_params.items():
                    if key.startswith("sslmode"):
                        params["sslmode"] = values[0]
        else:
            params["host"] = self.host
            params["port"] = self.port
            params["dbname"] = self.dbname
            params["user"] = self.username
            
            # Password handling
            if self.password:
                params["password"] = self.password
            elif os.getenv("PGPASSWORD"):
                params["password"] = os.getenv("PGPASSWORD")
            # .pgpass file will be used automatically by psycopg if no password provided
        
        # SSL configuration
        if self.ssl_mode:
            params["sslmode"] = self.ssl_mode
        if self.ssl_cert:
            params["sslcert"] = self.ssl_cert
        if self.ssl_key:
            params["sslkey"] = self.ssl_key
        if self.ssl_ca:
            params["sslrootcert"] = self.ssl_ca
        
        return params
    
    def connect(self) -> psycopg.Connection:
        """Establish database connection.
        
        Returns:
            psycopg.Connection: Database connection object
            
        Raises:
            psycopg.OperationalError: If connection fails
        """
        if self._conn and not self._conn.closed:
            return self._conn
        
        params = self._build_connection_params()
        
        # Prompt for password if needed
        if not params.get("password") and not os.getenv("PGPASSWORD"):
            import getpass
            params["password"] = getpass.getpass(f"Password for {params.get('user', 'user')}: ")
        
        try:
            self._conn = psycopg.connect(**params)
            return self._conn
        except psycopg.OperationalError as e:
            # Mask password in error messages
            error_msg = str(e)
            if params.get("password"):
                error_msg = error_msg.replace(params["password"], "***")
            raise psycopg.OperationalError(error_msg) from e
    
    def close(self):
        """Close database connection."""
        if self._conn and not self._conn.closed:
            self._conn.close()
            self._conn = None
    
    def __enter__(self):
        """Context manager entry."""
        return self.connect()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    @property
    def connection(self) -> Optional[psycopg.Connection]:
        """Get current connection."""
        return self._conn

