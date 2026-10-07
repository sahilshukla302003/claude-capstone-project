#!/bin/bash
# Stop: fires after every turn. Only print once the PR step has been logged as complete.
# Keep this grep in sync with the orchestrator's changelog format (Phase 4, Section 4).
grep -q "Step 9 (pr): COMPLETE" docs/changelog.md 2>/dev/null || exit 0
echo ""
echo "========================================"
echo "  PIPELINE RUN SUMMARY"
echo "========================================"

check_file() {
  if [ -s "$1" ]; then
    echo "  [OK]  $1"
  else
    echo "  [--]  $1 (not produced)"
  fi
}

check_file "docs/requirements.md"
check_file "docs/architecture.md"
check_file "docs/design-review.md"
check_file "docs/impl-plan.md"
check_file "output/reports/doc-sync-report.md"
check_file "output/reports/code-review.md"
check_file "output/test-results/results.md"

SRC_COUNT=$(find src/ -name "*.py" 2>/dev/null | wc -l)
TEST_COUNT=$(find tests/ -name "*.py" 2>/dev/null | wc -l)
echo "  [SRC] $SRC_COUNT Python source files in src/"
echo "  [TST] $TEST_COUNT Python test files in tests/"

echo ""
if [ -s "output/test-results/results.md" ]; then
  VERDICT=$(grep -i "Final Verdict" output/test-results/results.md | tail -1)
  echo "  Verification: $VERDICT"
fi
echo "========================================"
exit 0
