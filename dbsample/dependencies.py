"""Dependency resolution for tables and database objects."""

from typing import List, Dict, Set, Tuple
from collections import defaultdict, deque
from dbsample.schema import Table, ForeignKey


class DependencyResolver:
    """Resolve table dependencies for proper ordering."""
    
    def __init__(self, tables: List[Table]):
        """Initialize dependency resolver.
        
        Args:
            tables: List of tables to resolve dependencies for
        """
        self.tables = {t.qualified_name: t for t in tables}
        self._dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        self._reverse_graph: Dict[str, Set[str]] = defaultdict(set)
        self._build_graph()
    
    def _build_graph(self):
        """Build dependency graph from foreign keys."""
        for table in self.tables.values():
            table_name = table.qualified_name
            for fk in table.foreign_keys:
                ref_table = f"{fk.referenced_schema}.{fk.referenced_table}"
                if ref_table in self.tables:
                    # table depends on ref_table
                    self._dependency_graph[table_name].add(ref_table)
                    self._reverse_graph[ref_table].add(table_name)
    
    def get_insertion_order(self) -> List[str]:
        """Get tables in dependency order for insertion.
        
        Returns:
            List of qualified table names in insertion order
        """
        # Topological sort
        in_degree = {name: len(deps) for name, deps in self._dependency_graph.items()}
        
        # Initialize in_degree for all tables
        for table_name in self.tables:
            if table_name not in in_degree:
                in_degree[table_name] = 0
        
        queue = deque([name for name, degree in in_degree.items() if degree == 0])
        result = []
        
        while queue:
            table_name = queue.popleft()
            result.append(table_name)
            
            # Update in_degree for dependent tables
            for dependent in self._reverse_graph[table_name]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
        
        # Handle circular dependencies
        remaining = set(self.tables.keys()) - set(result)
        if remaining:
            # For circular dependencies, add them in arbitrary order
            # They will need special handling during sampling
            result.extend(remaining)
        
        return result
    
    def get_constraint_creation_order(self) -> List[str]:
        """Get tables in order for constraint creation (reverse of insertion order).
        
        Returns:
            List of qualified table names in constraint creation order
        """
        return list(reversed(self.get_insertion_order()))
    
    def get_dependent_tables(self, table_name: str) -> Set[str]:
        """Get all tables that depend on the given table.
        
        Args:
            table_name: Qualified table name
            
        Returns:
            Set of dependent table names
        """
        visited = set()
        queue = deque([table_name])
        dependents = set()
        
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            
            for dependent in self._reverse_graph.get(current, []):
                if dependent not in visited:
                    dependents.add(dependent)
                    queue.append(dependent)
        
        return dependents
    
    def get_dependencies(self, table_name: str) -> Set[str]:
        """Get all tables that the given table depends on.
        
        Args:
            table_name: Qualified table name
            
        Returns:
            Set of dependency table names
        """
        visited = set()
        queue = deque([table_name])
        dependencies = set()
        
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            
            for dep in self._dependency_graph.get(current, []):
                if dep not in visited:
                    dependencies.add(dep)
                    queue.append(dep)
        
        return dependencies
    
    def has_circular_dependencies(self) -> bool:
        """Check if there are circular dependencies.
        
        Returns:
            True if circular dependencies exist
        """
        insertion_order = self.get_insertion_order()
        return len(insertion_order) < len(self.tables)
    
    def get_circular_groups(self) -> List[List[str]]:
        """Get groups of tables involved in circular dependencies.
        
        Returns:
            List of groups, where each group is a list of table names in a cycle
        """
        visited = set()
        groups = []
        
        def find_cycle(start: str, path: List[str]) -> List[str]:
            """Find cycle starting from given node."""
            if start in path:
                # Found cycle
                cycle_start = path.index(start)
                return path[cycle_start:]
            
            if start in visited:
                return []
            
            visited.add(start)
            path.append(start)
            
            for neighbor in self._dependency_graph.get(start, []):
                cycle = find_cycle(neighbor, path.copy())
                if cycle:
                    return cycle
            
            return []
        
        for table_name in self.tables:
            if table_name not in visited:
                cycle = find_cycle(table_name, [])
                if cycle:
                    # Normalize cycle (start from lexicographically first)
                    start_idx = min(range(len(cycle)), key=lambda i: cycle[i])
                    normalized = cycle[start_idx:] + cycle[:start_idx]
                    groups.append(normalized)
        
        return groups

