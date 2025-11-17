#!/bin/bash
# Test script for pg-sample utility
# Usage: ./run_tests.sh [database_name] [username]

DB_NAME=${1:-pg_sample_test}
DB_USER=${2:-postgres}
HOST=${3:-localhost}

echo "========================================="
echo "Testing pg-sample utility"
echo "Database: $DB_NAME"
echo "User: $DB_USER"
echo "Host: $HOST"
echo "========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

test_command() {
    local test_name=$1
    local command=$2
    local expected_file=$3
    
    echo -e "${YELLOW}Test: $test_name${NC}"
    echo "Command: $command"
    
    if eval "$command"; then
        if [ -n "$expected_file" ] && [ -f "$expected_file" ]; then
            echo -e "${GREEN}✓ PASSED${NC}"
            TESTS_PASSED=$((TESTS_PASSED + 1))
        elif [ -z "$expected_file" ]; then
            echo -e "${GREEN}✓ PASSED${NC}"
            TESTS_PASSED=$((TESTS_PASSED + 1))
        else
            echo -e "${RED}✗ FAILED: Expected file $expected_file not created${NC}"
            TESTS_FAILED=$((TESTS_FAILED + 1))
        fi
    else
        echo -e "${RED}✗ FAILED: Command returned error${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
    echo ""
}

# Test 1: Basic connection and help
echo "=== Test 1: Help command ==="
test_command "Help command" "pg-sample --help" ""

# Test 2: Basic sampling
echo "=== Test 2: Basic sampling (10 rows per table) ==="
test_command "Basic sampling" \
    "pg-sample --host $HOST --username $DB_USER --dbname $DB_NAME --limit '*=10' --file test_basic.sql --verbose" \
    "test_basic.sql"

# Test 3: Custom limits
echo "=== Test 3: Custom row limits ==="
test_command "Custom limits" \
    "pg-sample --host $HOST --username $DB_USER --dbname $DB_NAME --limit 'users=3,orders=2,*=1' --file test_custom.sql --verbose" \
    "test_custom.sql"

# Test 4: Column exclusion
echo "=== Test 4: Column exclusion ==="
test_command "Column exclusion" \
    "pg-sample --host $HOST --username $DB_USER --dbname $DB_NAME --exclude-column 'users.password,*.secret_key' --limit '*=5' --file test_excluded.sql --verbose" \
    "test_excluded.sql"

# Test 5: Schema filtering
echo "=== Test 5: Schema filtering ==="
test_command "Schema filtering" \
    "pg-sample --host $HOST --username $DB_USER --dbname $DB_NAME --schema public --exclude-schema archive --limit '*=5' --file test_filtered.sql --verbose" \
    "test_filtered.sql"

# Test 6: Deterministic ordering
echo "=== Test 6: Deterministic ordering ==="
test_command "Deterministic ordering" \
    "pg-sample --host $HOST --username $DB_USER --dbname $DB_NAME --ordered --ordered-desc --limit '*=5' --file test_ordered.sql --verbose" \
    "test_ordered.sql"

# Test 7: Data-only export
echo "=== Test 7: Data-only export ==="
test_command "Data-only export" \
    "pg-sample --host $HOST --username $DB_USER --dbname $DB_NAME --data-only --limit '*=5' --file test_data_only.sql --verbose" \
    "test_data_only.sql"

# Test 8: Audit trail
echo "=== Test 8: Audit trail ==="
test_command "Audit trail" \
    "pg-sample --host $HOST --username $DB_USER --dbname $DB_NAME --limit '*=5' --file test_audit.sql --audit-file test_audit.json --verbose" \
    "test_audit.json"

# Test 9: Verify SQL syntax (basic check)
echo "=== Test 9: Verify SQL syntax ==="
if [ -f "test_basic.sql" ]; then
    echo "Checking SQL file structure..."
    if grep -q "BEGIN;" test_basic.sql && \
       grep -q "CREATE TABLE" test_basic.sql && \
       grep -q "INSERT INTO" test_basic.sql && \
       grep -q "COMMIT;" test_basic.sql; then
        echo -e "${GREEN}✓ SQL structure looks correct${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}✗ SQL structure incomplete${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
else
    echo -e "${RED}✗ test_basic.sql not found${NC}"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi
echo ""

# Summary
echo "========================================="
echo "Test Summary"
echo "========================================="
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed${NC}"
    exit 1
fi

