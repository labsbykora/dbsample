@echo off
REM Test script for dbsample utility (Windows)
REM Usage: run_tests.bat [database_name] [username] [host]

setlocal enabledelayedexpansion

set DB_NAME=%1
if "%DB_NAME%"=="" set DB_NAME=dbsample_test

set DB_USER=%2
if "%DB_USER%"=="" set DB_USER=postgres

set HOST=%3
if "%HOST%"=="" set HOST=localhost

echo =========================================
echo Testing dbsample utility
echo Database: %DB_NAME%
echo User: %DB_USER%
echo Host: %HOST%
echo =========================================
echo.

set TESTS_PASSED=0
set TESTS_FAILED=0

REM Test 1: Help command
echo === Test 1: Help command ===
dbsample --help >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [PASS] Help command
    set /a TESTS_PASSED+=1
) else (
    echo [FAIL] Help command
    set /a TESTS_FAILED+=1
)
echo.

REM Test 2: Basic sampling
echo === Test 2: Basic sampling (10 rows per table) ===
dbsample --host %HOST% --username %DB_USER% --dbname %DB_NAME% --limit "*=10" --file test_basic.sql --verbose
if exist test_basic.sql (
    echo [PASS] Basic sampling
    set /a TESTS_PASSED+=1
) else (
    echo [FAIL] Basic sampling - file not created
    set /a TESTS_FAILED+=1
)
echo.

REM Test 3: Custom limits
echo === Test 3: Custom row limits ===
dbsample --host %HOST% --username %DB_USER% --dbname %DB_NAME% --limit "users=3,orders=2,*=1" --file test_custom.sql --verbose
if exist test_custom.sql (
    echo [PASS] Custom limits
    set /a TESTS_PASSED+=1
) else (
    echo [FAIL] Custom limits - file not created
    set /a TESTS_FAILED+=1
)
echo.

REM Test 4: Column exclusion
echo === Test 4: Column exclusion ===
dbsample --host %HOST% --username %DB_USER% --dbname %DB_NAME% --exclude-column "users.password,*.secret_key" --limit "*=5" --file test_excluded.sql --verbose
if exist test_excluded.sql (
    echo [PASS] Column exclusion
    set /a TESTS_PASSED+=1
) else (
    echo [FAIL] Column exclusion - file not created
    set /a TESTS_FAILED+=1
)
echo.

REM Test 5: Schema filtering
echo === Test 5: Schema filtering ===
dbsample --host %HOST% --username %DB_USER% --dbname %DB_NAME% --schema public --exclude-schema archive --limit "*=5" --file test_filtered.sql --verbose
if exist test_filtered.sql (
    echo [PASS] Schema filtering
    set /a TESTS_PASSED+=1
) else (
    echo [FAIL] Schema filtering - file not created
    set /a TESTS_FAILED+=1
)
echo.

REM Test 6: Deterministic ordering
echo === Test 6: Deterministic ordering ===
dbsample --host %HOST% --username %DB_USER% --dbname %DB_NAME% --ordered --ordered-desc --limit "*=5" --file test_ordered.sql --verbose
if exist test_ordered.sql (
    echo [PASS] Deterministic ordering
    set /a TESTS_PASSED+=1
) else (
    echo [FAIL] Deterministic ordering - file not created
    set /a TESTS_FAILED+=1
)
echo.

REM Test 7: Data-only export
echo === Test 7: Data-only export ===
dbsample --host %HOST% --username %DB_USER% --dbname %DB_NAME% --data-only --limit "*=5" --file test_data_only.sql --verbose
if exist test_data_only.sql (
    echo [PASS] Data-only export
    set /a TESTS_PASSED+=1
) else (
    echo [FAIL] Data-only export - file not created
    set /a TESTS_FAILED+=1
)
echo.

REM Test 8: Audit trail
echo === Test 8: Audit trail ===
dbsample --host %HOST% --username %DB_USER% --dbname %DB_NAME% --limit "*=5" --file test_audit.sql --audit-file test_audit.json --verbose
if exist test_audit.json (
    echo [PASS] Audit trail
    set /a TESTS_PASSED+=1
) else (
    echo [FAIL] Audit trail - file not created
    set /a TESTS_FAILED+=1
)
echo.

REM Test 9: Verify SQL syntax
echo === Test 9: Verify SQL syntax ===
if exist test_basic.sql (
    findstr /C:"BEGIN;" test_basic.sql >nul && findstr /C:"CREATE TABLE" test_basic.sql >nul && findstr /C:"INSERT INTO" test_basic.sql >nul && findstr /C:"COMMIT;" test_basic.sql >nul
    if %ERRORLEVEL% EQU 0 (
        echo [PASS] SQL structure looks correct
        set /a TESTS_PASSED+=1
    ) else (
        echo [FAIL] SQL structure incomplete
        set /a TESTS_FAILED+=1
    )
) else (
    echo [FAIL] test_basic.sql not found
    set /a TESTS_FAILED+=1
)
echo.

REM Summary
echo =========================================
echo Test Summary
echo =========================================
echo Passed: %TESTS_PASSED%
echo Failed: %TESTS_FAILED%
echo.

if %TESTS_FAILED% EQU 0 (
    echo All tests passed!
    exit /b 0
) else (
    echo Some tests failed
    exit /b 1
)

