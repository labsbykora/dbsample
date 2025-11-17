#!/bin/bash
# Test importing a generated sample SQL file
# Usage: ./test_import.sh [sample_file] [test_db_name]

SAMPLE_FILE=${1:-test_basic.sql}
TEST_DB=${2:-dbsample_test_import}
DB_USER=${3:-postgres}

echo "========================================="
echo "Testing SQL Import"
echo "Sample file: $SAMPLE_FILE"
echo "Test database: $TEST_DB"
echo "========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if sample file exists
if [ ! -f "$SAMPLE_FILE" ]; then
    echo -e "${RED}Error: Sample file $SAMPLE_FILE not found${NC}"
    exit 1
fi

# Drop test database if it exists
echo -e "${YELLOW}Dropping test database if it exists...${NC}"
dropdb -U $DB_USER $TEST_DB 2>/dev/null || true

# Create test database
echo -e "${YELLOW}Creating test database...${NC}"
if createdb -U $DB_USER $TEST_DB; then
    echo -e "${GREEN}✓ Database created${NC}"
else
    echo -e "${RED}✗ Failed to create database${NC}"
    exit 1
fi

# Import SQL file
echo -e "${YELLOW}Importing SQL file...${NC}"
if psql -U $DB_USER -d $TEST_DB -f "$SAMPLE_FILE" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ SQL imported successfully${NC}"
else
    echo -e "${RED}✗ Import failed${NC}"
    echo "Checking for errors..."
    psql -U $DB_USER -d $TEST_DB -f "$SAMPLE_FILE" 2>&1 | tail -20
    dropdb -U $DB_USER $TEST_DB
    exit 1
fi

# Verify foreign key constraints
echo -e "${YELLOW}Verifying foreign key constraints...${NC}"
FK_COUNT=$(psql -U $DB_USER -d $TEST_DB -t -c "
    SELECT COUNT(*) 
    FROM pg_constraint 
    WHERE contype = 'f';
" | xargs)

if [ "$FK_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ Found $FK_COUNT foreign key constraint(s)${NC}"
    
    # Check for constraint violations
    echo -e "${YELLOW}Checking for constraint violations...${NC}"
    VIOLATIONS=$(psql -U $DB_USER -d $TEST_DB -t -c "
        SELECT COUNT(*) 
        FROM information_schema.table_constraints tc
        WHERE tc.constraint_type = 'FOREIGN KEY'
        AND NOT EXISTS (
            SELECT 1 FROM pg_constraint pc
            WHERE pc.conname = tc.constraint_name
            AND pc.convalidated = true
        );
    " 2>/dev/null | xargs)
    
    if [ "$VIOLATIONS" = "0" ] || [ -z "$VIOLATIONS" ]; then
        echo -e "${GREEN}✓ No constraint violations detected${NC}"
    else
        echo -e "${RED}✗ Found constraint violations${NC}"
    fi
else
    echo -e "${YELLOW}⚠ No foreign key constraints found${NC}"
fi

# Show table row counts
echo ""
echo -e "${YELLOW}Table row counts:${NC}"
psql -U $DB_USER -d $TEST_DB -c "
    SELECT 
        schemaname || '.' || tablename AS table_name,
        n_live_tup AS row_count
    FROM pg_stat_user_tables
    ORDER BY schemaname, tablename;
"

# Ask if user wants to keep the test database
echo ""
read -p "Keep test database $TEST_DB? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Dropping test database...${NC}"
    dropdb -U $DB_USER $TEST_DB
    echo -e "${GREEN}✓ Test database dropped${NC}"
else
    echo -e "${GREEN}Test database $TEST_DB kept for inspection${NC}"
fi

echo ""
echo -e "${GREEN}Import test completed!${NC}"

