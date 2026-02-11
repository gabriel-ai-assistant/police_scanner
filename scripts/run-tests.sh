#!/usr/bin/env bash

# Police Scanner Analytics Platform - Test Runner
# Executes all test suites with coverage reporting

set -e  # Exit on error

echo "========================================="
echo "Police Scanner - Test Suite"
echo "========================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track test results
BACKEND_TESTS_PASSED=0
FRONTEND_TESTS_PASSED=0

# Backend tests
echo "Running backend tests..."
echo "------------------------"

if pytest app_api/tests/ app_scheduler/tests/ app_transcribe/tests/ -v --cov=app_api --cov=app_scheduler --cov=app_transcribe --cov-report=term --cov-report=html; then
    echo -e "${GREEN}✓ Backend tests passed${NC}"
    BACKEND_TESTS_PASSED=1
else
    echo -e "${RED}✗ Backend tests failed${NC}"
fi

echo ""
echo "Coverage report generated in htmlcov/"
echo ""

# Frontend tests
echo "Running frontend tests..."
echo "------------------------"

cd frontend
if npm test -- --passWithNoTests; then
    echo -e "${GREEN}✓ Frontend tests passed${NC}"
    FRONTEND_TESTS_PASSED=1
else
    echo -e "${RED}✗ Frontend tests failed${NC}"
fi
cd ..

echo ""
echo "========================================="
echo "Test Summary"
echo "========================================="

if [ $BACKEND_TESTS_PASSED -eq 1 ]; then
    echo -e "Backend:  ${GREEN}PASSED${NC}"
else
    echo -e "Backend:  ${RED}FAILED${NC}"
fi

if [ $FRONTEND_TESTS_PASSED -eq 1 ]; then
    echo -e "Frontend: ${GREEN}PASSED${NC}"
else
    echo -e "Frontend: ${RED}FAILED${NC}"
fi

echo ""

# Exit with error if any tests failed
if [ $BACKEND_TESTS_PASSED -eq 1 ] && [ $FRONTEND_TESTS_PASSED -eq 1 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Please fix before deploying.${NC}"
    exit 1
fi
